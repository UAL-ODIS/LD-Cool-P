from os.path import exists, join, dirname, basename, getctime
from os import walk, stat, symlink
from datetime import datetime
import shutil
from glob import glob
import re

# Template engine
from jinja2 import Environment, FileSystemLoader
from jinja2.ext import loopcontrols
from html2text import html2text

# Logging
from redata.commons.logger import log_stdout

from ... import metadata
from ....admin import permissions, move

# Read in default configuration settings
from ....config import config_default_dict

from ...api.qualtrics import Qualtrics
from ...depositor_name import DepositorName


class ReadmeClass:
    """
    Purpose:
      A ReadmeClass object for retrieval and population of README.txt
      files.  It uses existing metadata information from Figshare to
      populate common information that are provided

    Attributes
    ----------
    dn : DepositorName object
      Contains information about the depositor and author(s)

    folderName : str
      Folder name identifying depositor and corresponding author

    article_id : int
      Figshare article ID

    article_dict : dict
      dictionary containing curation details

    data_path : str
      Path DATA folder (this is the working copy and not the ORIGINAL_DATA)

    readme_file_path : str
      Full filename for exported README.txt

    readme_template: jinja2.environment.Template

    figshare_readme_dict : dict
      Contains metadata information to provide to jinja template

    qualtrics_readme_dict : dict
      Contains metadata information to provide to jinja template

    Methods
    -------
    get_readme_files()
      Return list of README files in the ORIGINAL_DATA path

    check_for_readme()
      Check if a README file is provided and provide list of README files

    select_template(update)
      Select README template to use from template repository

    save_template()
      Save either default or user-provided templates in DATA path

    import_template()
      Returns a jinja2 template by importing markdown README file (README_template.md)

    retrieve article_metadata()
      Returns a dictionary containing metadata for jinja2 template

    construct()
      Create README.txt file with jinja2 README template and populate with metadata information

    update()
      Update README.txt file for changes in figshare or Qualtrics dictionary

    main()
      Construct README.txt by calling retrieve
    """

    def __init__(self, dn: DepositorName, config_dict=config_default_dict,
                 update=False, q: Qualtrics = None, interactive=True,
                 log=None):
        self.config_dict = config_dict
        self.interactive = interactive

        self.dn = dn
        self.folderName = self.dn.folderName
        self.article_id = self.dn.article_id
        self.article_dict = self.dn.curation_dict

        if isinstance(log, type(None)):
            self.log = log_stdout()
        else:
            self.log = log

        self.log.info("")
        if not update:
            self.log.info("** STARTING README.txt CONSTRUCTION **")
            if self.interactive:
                self.log.info("PROMPT: Do you wish to create a README file?")
                self.user_response = input(
                    "PROMPT: Type 'Yes'/'yes'. Anything else will exit : "
                ).lower()
                self.log.info(f"RESPONSE: {self.user_response}")
            else:
                self.log.info("Interactive mode disabled. Always creating README.txt")
                self.user_response = 'yes'
        else:
            self.log.info("** UPDATING README.txt **")
            self.user_response = 'yes'

        # Use or initialize Qualtrics object
        if self.user_response != 'yes':
            return

        self.curation_dict = self.config_dict['curation']
        self.root_directory_main = self.curation_dict[self.curation_dict['parent_dir']]
        self.funders_macro = join(self.curation_dict['macros_folder'], self.curation_dict['funders_macro'])

        # Always obtain current data curation stage
        self.mc = move.MoveClass(curation_dict=self.curation_dict)
        self.current_stage = self.mc.get_source_stage(self.folderName)
        self.log.info(f"Current stage: {self.current_stage}")
        self.root_directory = join(self.root_directory_main,
                                   self.current_stage)

        # Paths
        self.folder_path = join(self.root_directory, self.folderName)
        self.metadata_path = join(self.folder_path,
                                  self.curation_dict['folder_metadata'])  # METADATA
        self.data_path = join(self.folder_path,
                              self.curation_dict['folder_copy_data'])  # DATA
        self.original_data_path = join(self.folder_path,
                                       self.curation_dict['folder_data'])  # ORIGINAL_DATA

        # This is the full path of the final README.txt file for creation
        self.readme_file_path = join(self.data_path, 'README.txt')

        # Symlink template name in METADATA
        self.default_readme_file = self.curation_dict['readme_template']

        if q:
            self.q = q
        else:
            self.q = Qualtrics(config_dict=self.config_dict,
                               mc=self.mc, interactive=interactive, log=self.log)

        # Retrieve Figshare metadata for jinja template engine
        self.figshare_readme_dict = self.retrieve_article_metadata()

        # Retrieve Qualtrics README information for jinja template engine
        self.qualtrics_readme_dict = self.retrieve_qualtrics_readme()

        # Retrieve list of README files provided by user
        self.README_files = self.get_readme_files()

        try:
            # Define template_source
            self.template_source = self.check_for_readme()

            if self.template_source == 'default':
                self.readme_template = self.select_template()
            else:
                self.readme_template = 'user_readme_template.md'

            # Save copy of template in DATA as README_template.md
            self.save_template()

            # Import README template as jinja2 template
            self.jinja_template = self.import_template()
        except SystemError:
            self.template_source = 'unknown'
            self.log.warning("More than one README files found!")

    def get_readme_files(self):
        """Return list of README files in the ORIGINAL_DATA path"""
        README_files = glob(join(self.original_data_path, 'README*.txt'))
        README_files += glob(join(self.original_data_path, 'README*.md'))

        return README_files

    def check_for_readme(self):
        """Check if a README file is provided and provide list of README files"""

        if len(self.README_files) == 0:
            self.log.info("No README files found.")
            self.log.info(f"Note: You will be asked to select from default templates")
            template_source = 'default'
        else:
            if len(self.README_files) == 1:
                self.log.info("Only one README file found!")

                self.log.info("PROMPT: Type 'Yes'/'yes' if you wish to use as template.")
                if self.interactive:
                    src_input = input("PROMPT: Anything else will use 'default' : ")
                    self.log.info(f"RESPONSE: {src_input}")
                else:
                    self.log.info("Interactive mode disabled. Using default")
                    src_input = ''

                if src_input.lower() == 'yes':
                    template_source = 'user'
                else:
                    template_source = 'default'
            else:
                self.log.warn("More than one README file found!")
                self.log.warn("Manual intervention needed ...")
                raise SystemError
                # print(f"Select and save a README file in {copy_path} as {readme_template}")

        return template_source

    def select_template(self):
        """Select README template to use from template repository"""

        self.log.info("")
        self.log.info("** SELECTING README TEMPLATE **")

        # Retrieve LD-Cool-P templates
        template_dir = join(dirname(__file__), 'templates/')
        template_list = sorted(glob(template_dir + '*.md'), key=getctime)

        if len(template_list) == 0:
            self.log.warning("Missing templates!!!")
            raise SystemError

        # Check that templates exists for deposit
        t_list = [basename(md_file) for md_file in
                  glob(join(self.metadata_path, '*.md'))]
        if len(t_list) == 0:
            template_list = [basename(t_file) for t_file in template_list]
            if len(template_list) == 1:
                self.log.info(f"Only one template found: {template_list[0]}. Using!")
                template_i = 0
            else:
                self.log.info("List of README templates: ")
                for i, template_file in enumerate(template_list):
                    self.log.info(f"  ({i}): {template_file}")
                template_i = int(input("Select from above list (enter number ONLY) : "))
                self.log.info(f"RESPONSE: {template_i} == {template_list[template_i]}")

            return template_list[template_i]
        else:
            t_list.remove(self.default_readme_file)
            return t_list[0]

    def save_template(self):
        """Save either default or user-provided templates in DATA path"""

        symlink_file = join(self.metadata_path, self.default_readme_file)

        dest_file = join(self.metadata_path, self.readme_template)

        funders_macro_file_src = join(dirname(__file__), 'templates',
                                self.funders_macro)
        funders_macro_file_dest = join(self.metadata_path, self.curation_dict['funders_macro'])

        if not exists(dest_file):
            self.log.info(f"Saving {self.readme_template} template in METADATA ...")

            if self.template_source == 'default':
                src_file = join(dirname(__file__), 'templates',
                                self.readme_template)
            else:
                src_file = self.README_files[0]

            self.log.info(f"Source file name: {src_file}")
            shutil.copy(src_file, dest_file)
            shutil.copy(funders_macro_file_src, funders_macro_file_dest)
        else:
            self.log.info(f"{dest_file} exists. Not overwriting template!")

        if not exists(symlink_file):
            symlink(self.readme_template, symlink_file)
        else:
            self.log.info(f"{symlink_file} symbolic file link exists. Not overwriting!")

    def import_template(self):
        """Returns a jinja2 template by importing README markdown template (README_template.md)"""

        file_loader = FileSystemLoader(self.metadata_path)
        env = Environment(loader=file_loader, lstrip_blocks=True, trim_blocks=True, extensions=[loopcontrols])

        jinja_template = env.get_template(self.default_readme_file)
        return jinja_template

    def retrieve_article_metadata(self):
        """
        Purpose:
          Retrieve metadata from figshare API to strip out information to
          populate in README.txt file for basic content

        :return readme_dict: dict containing essential metadata for README.txt
        """

        readme_dict = dict()

        # Retrieve title of deposit
        readme_dict['title'] = self.article_dict['item']['title']

        # Retrieve preferred citation. Default: ReDATA in DataCite format
        # This forces a period after the year and ensures multiple rows
        # with the last two rows merged for simplicity
        # Bug: v0.17.6 handles periods in author list (e.g., initials)
        single_str_citation = self.article_dict['item']['citation']
        pre_processed_str = single_str_citation.replace('):', ').')
        # Match spaces following group 1, only if followed by group 2
        END_SENT = re.compile('((?<=[.!?])|(?<=\.\":)) +(?=[A-Z,0-9])')
        # Filter for empty list entry
        citation_list = list(filter(None, END_SENT.split(pre_processed_str)))
        readme_dict['preferred_citation'] = citation_list

        # Retrieve DOI info. Reserve if it does not exist
        if not self.article_dict['item']['doi']:
            # Reserve DOI
            doi_string = self.dn.fs_admin.reserve_doi(self.article_id)

            if not doi_string:  # If not reserving DOI, note this in README file
                fs_prefix = "10.0166/FK2.stagefigshare" if self.dn.fs_admin.dict['stage'] \
                    else "10.25422/azu.data"
                readme_dict['doi'] = f"{fs_prefix}.{self.article_id} [DOI NOT MINTED!]"
            else:
                readme_dict['doi'] = doi_string
        else:
            # DOI reserved before submission or in a previous step of the workflow
            readme_dict['doi'] = f"{self.article_dict['item']['doi']}"

        readme_dict['lastname'] = self.dn.name_dict['surName']
        readme_dict['firstname'] = self.dn.name_dict['firstName']
        readme_dict['email'] = self.dn.name_dict['depositor_email']

        # Retrieve license
        readme_dict['license'] = self.article_dict['item']['license']['name']

        # Retrieve author
        readme_dict['first_author'] = \
            self.article_dict['item']['authors'][0]['full_name']

        # Retrieve description (single string), strip vertical white space
        description = html2text(self.article_dict['item']['description'])
        # Don't think we need this
        # description = self.article_dict['item']['description'].replace('<div>', '')
        # description = html2text(description.replace('</div>', ''))

        # Strip ReDATA footer
        if self.curation_dict['footer'] in description:
            self.log.info("Stripping footer")

            strip_text = description.partition(self.curation_dict['footer'])[0]
            if not strip_text.endswith("\n\n"):
                self.log.info("No carriage returns")
            while strip_text.endswith("  \n\n"):
                strip_text = strip_text[:-4]
            while strip_text.endswith("\n\n"):
                strip_text = strip_text[:-2]
            while strip_text.endswith("\n"):
                strip_text = strip_text[:-1]

            readme_dict['description'] = strip_text
        else:
            self.log.info("No footer to strip")
            readme_dict['description'] = description

        # Retrieve funder details as a list of dicts
        readme_dict['funders'] = self.article_dict['item']['funding_list']

        # Retrieve references as list
        readme_dict['references'] = self.article_dict['item']['references']

        # Retrieve related materials as a list of dicts
        readme_dict['related_materials'] = self.article_dict['item']['related_materials']

        return readme_dict

    def retrieve_qualtrics_readme(self):
        """Retrieve README custom information from Qualtrics form"""

        self.log.info("")
        self.log.info("** IDENTIFYING README FORM RESPONSE **")

        readme_dict = self.q.retrieve_qualtrics_readme(self.dn)

        return readme_dict

    def construct(self):
        """Create README.txt file with jinja2 README template and populate with metadata information"""

        if not exists(self.readme_file_path):
            self.log.info(f"Constructing README.txt file based on {self.template_source} template ...")

            # Write file
            self.log.info(f"Writing file : {self.readme_file_path}")
            f = open(self.readme_file_path, 'w')

            content_list = self.jinja_template.render(figshare_dict=self.figshare_readme_dict,
                                                      qualtrics_dict=self.qualtrics_readme_dict)
            f.writelines(content_list)
            f.close()

            out_file_prefix = f"readme_original_{self.article_id}"
            self.save_metadata(out_file_prefix=out_file_prefix)
        else:
            self.log.warn("Default README.txt file found! Not overwriting with template!")

        # Set permission for rwx
        permissions.curation(self.readme_file_path)

    def update(self):
        """Update README.txt file for changes in figshare or Qualtrics dictionary"""

        # Retrieve new README.txt file first
        content_list = self.jinja_template.render(figshare_dict=self.figshare_readme_dict,
                                                  qualtrics_dict=self.qualtrics_readme_dict)
        if exists(self.readme_file_path):
            f = open(self.readme_file_path, 'r')
            readme_old = ''.join(f.readlines())

            if content_list == readme_old:
                self.log.warn("README.txt did not change")
                self.log.info("Not replacing file")
            else:
                self.log.info("README.txt changed. Updating!")
                st = stat(self.readme_file_path)
                mod_time = datetime.fromtimestamp(st.st_mtime)
                mod_time_str = mod_time.isoformat(timespec='seconds').\
                    replace(':', '')
                backup_copy_filename = self.readme_file_path.replace('.txt', f'_{mod_time_str}.txt')
                self.log.info(f"Saving previous copy as : {basename(backup_copy_filename)}")
                shutil.copyfile(self.readme_file_path, backup_copy_filename)

                self.log.info(f"Writing updated README.txt file : {self.readme_file_path}")
                f = open(self.readme_file_path, 'w')
                f.writelines(content_list)
                f.close()

                # Saving Qualtrics README for metadata for updated README.txt
                cur_time = datetime.now()
                out_file_prefix = f"readme_revised_{self.article_id}_" + \
                                  f"{cur_time.isoformat(timespec='seconds').replace(':', '')}"
                self.save_metadata(out_file_prefix=out_file_prefix)
        else:
            self.log.info("README.txt does not exist. Creating new one")

            self.log.info(f"Writing README.txt file : {self.readme_file_path}")
            f = open(self.readme_file_path, 'w')
            f.writelines(content_list)
            f.close()

    def main(self):
        """Main function for README file construction"""

        if self.user_response == "yes":
            if self.template_source == 'unknown':
                self.log.warn(f"Multiple README files. Unable to save {self.readme_template} and README.txt")
                raise SystemError

            self.construct()
        else:
            raise SystemExit("SKIPPING README.txt CONSTRUCTION")

    def save_metadata(self, out_file_prefix: str = 'readme'):
        """Save README metadata to JSON file"""

        response_dict = {
            'figshare': self.figshare_readme_dict,
            'qualtrics': self.qualtrics_readme_dict,
        }

        root_directory = join(
            self.curation_dict[self.curation_dict['parent_dir']],
            self.current_stage,
            self.dn.folderName
        )
        metadata_directory = self.curation_dict['folder_metadata']

        metadata.save_metadata(response_dict, out_file_prefix,
                               metadata_source='README',
                               root_directory=root_directory,
                               metadata_directory=metadata_directory,
                               log=self.log)


def walkthrough(data_path, ignore='', log=None):
    """
    Purpose:
      Perform walkthrough to find other README files

    :param data_path: path to DATA folder
    :param ignore: full path of default README.txt to ignore
    :param log: logger.LogClass object. Default is stdout via python logging
    :return:
    """

    if isinstance(log, type(None)):
        log = log_stdout()
    else:
        log = log

    for dir_path, dir_names, files in walk(data_path):
        for file in files:
            if 'README' in file.upper():  # case insensitive
                file_fullname = join(dir_path, file)
                if file_fullname != ignore:
                    log.info(f"File exists : {file_fullname}")
