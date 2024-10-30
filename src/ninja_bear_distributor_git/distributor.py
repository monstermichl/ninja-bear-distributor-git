from __future__ import annotations
import os
import re
import subprocess
import tempfile

from typing import Dict, Tuple
from getpass import getpass
from os.path import join

from ninja_bear import DistributorBase, DistributorCredentials, DistributeInfo

class NoRepositoryUrlProvidedException(Exception):
    def __init__(self):
        super().__init__('No repository URL has been provided')


class NoPasswordProvidedException(Exception):
    def __init__(self, url):
        super().__init__(f'No password has been provided for {url}')


class NoCommitMessageProvidedException(Exception):
    def __init__(self, file_name, url):
        super().__init__(f'No commit message has been provided for {file_name} ({url})')


class GitProblemException(Exception):
    def __init__(self, problem: str, additional_info: str=''):
        problem = f'{problem}\n{additional_info}' if additional_info else problem
        super().__init__(problem)


class GitVersionException(Exception):
    def __init__(self, check_version: GitVersion, git_version: GitVersion):
        super().__init__(f'Invalid git version. Required: {check_version}, actual: {git_version}')


def execute_command(commands: str, directory=None) -> Tuple[int, str, str]:
        # https://www.squash.io/how-to-execute-a-program-or-system-command-in-python/.
        result = subprocess.run(commands, capture_output=True, text=True, shell=True, cwd=directory)
        return result.returncode, result.stdout, result.stderr


class GitVersion:
    major: str
    minor: str
    patch: str

    def __init__(self, major: int, minor: int, patch: int):
        """
        Constructor

        :param major: Major version.
        :type major:  int
        :param minor: Minor version.
        :type minor:  int
        :param patch: Patch version.
        :type patch:  int
        """
        self.major = major
        self.minor = minor
        self.patch = patch

    @staticmethod
    def from_git() -> GitVersion:
        """
        Retrieves the git version by calling git --version.

        :raises GitProblemException: Raised if the Git version could not be evaluated.

        :return: GitVersion instance with the actual Git version.
        :rtype:  GitVersion
        """
        code, text, _ = execute_command('git --version')
        version_text = text if code == 0 else ''

        if code != 0:
            raise GitProblemException('Git version could not be evaluated')
        return GitVersion.from_string(version_text)

    @staticmethod
    def from_string(version_string: str) -> GitVersion:
        """
        Turns a version string.

        :param version_string: Version string which contains the version in the form of <major>.<minor>.<patch>.
        :type version_string:  str

        :return: GitVersion instance with the data from the version string.
        :rtype:  GitVersion
        """
        version = GitVersion(0, 0, 0)
        match = re.search('\d+\.\d+\.\d+', version_string)

        if match:
            parts = match.group(0).split('.')

            version.major = int(parts[0])
            version.minor = int(parts[1])
            version.patch = int(parts[2])
        return version
    
    def __str__(self) -> str:
        return f'{self.major}.{self.minor}.{self.patch}'


class Distributor(DistributorBase):
    _MIN_GIT_VERSION = GitVersion(2, 29, 0)  # Needs at least git version 2.29.0 as it introduced partial-clone (https://www.git-scm.com/docs/partial-clone).

    def __init__(self, config: Dict[str, str], credentials: DistributorCredentials=None):
        """
        Constructor

        :param url:         Git repository URL.
        :type url:          str
        :param target_path: Relative target path within the repo.
        :type target_path:  str
        :param user:        Git user.
        :type user:         str
        :param password:    Git user password or token.
        :type password:     str
        """
        super().__init__(config, credentials)

        target_path, _ = self.from_config('path')  # Use root directory as default path.

        self._url, _ = self.from_config('url')
        self._target_path = target_path if target_path else ''  # Use root directory as default path.
        self._user, self._user_key_exists = self.from_config('user')
        self._password, self._password_key_exists = self.from_config('password')
        self._branch, _ = self.from_config('branch')
        self._message, _ = self.from_config('message')

        self._check_preconditions()
        self._check_git_version()
        
    def _check_preconditions(self):
        """
        Check preconditions.

        :raises NoRepositoryUrlProvidedException: Raised if no Git server URL has been provided.
        :raises NoPasswordProvidedException:      Raised if no password has been provided.
        """
        url = self._url

        # Make sure an URL has been provided.
        if not url:
            raise NoRepositoryUrlProvidedException()
        
        # Prompt user input if required.
        if not self._user and self._user_key_exists:
            self._user = input(f'User ({url}): ')
        
        # Prompt password input if required.
        if not self._password and self._password_key_exists:
            self._password = getpass(f'Password ({url}): ', )

        # Make sure a password has been provided.
        if not self._password:
            raise NoPasswordProvidedException(url)
        
    def _check_git_version(self):
        """
        Checks if the installed Git version is suitable.

        :raises GitVersionException: Raised if Git does not fulfill the minimum required version.
        """
        # Retrieve Git version.
        git_version = GitVersion.from_git()
        
        if git_version.major < self._MIN_GIT_VERSION.major or \
           git_version.minor < self._MIN_GIT_VERSION.minor or \
           git_version.patch < self._MIN_GIT_VERSION.patch:
            raise GitVersionException(self._MIN_GIT_VERSION, git_version)

    def _distribute(self, info: DistributeInfo) -> DistributorBase:
        """
        Method to distribute a generated config to a Git server.

        :param info: Contains the required information to distribute the generated config.
        :type info:  DistributeInfo

        :raises GitProblemException: Raised on different Git problems.

        :return: The current GitDistributor instance.
        :rtype:  GitDistributor
        """
        file_name = info.file_name
        data = info.data

        # Create temporary folder to clone the git repo into and work with it.
        with tempfile.TemporaryDirectory() as temp_dir:
            SEPARATOR = '://'
            url = self._url
            url_parts = url.split(SEPARATOR)
            protocol = url_parts[0] if len(url_parts) > 1 else 'https'
            temp_url = url_parts[1] if len(url_parts) > 1 else url_parts[0]
            separator = SEPARATOR if protocol else ''
            user = self._user if self._user else ''
            password = self._password if self._password else ''
            colon = ':' if user and password else ''
            at = '@' if user or password else ''
            branch_command = f'--branch {self._branch}' if self._branch else ''
            url_with_credentials = f'{protocol}{separator}{user}{colon}{password}{at}{temp_url}'
            password = None

            code, _, stderr = execute_command(
                # Space before git-command to not log in history (might be disabled by the system).
                f' git clone {branch_command} --filter=blob:none --no-checkout {url_with_credentials} {temp_dir}',
            )

            # If clone was successful, go on.
            if code == 0:
                # Only clone desired target folder.
                code, _, stderr = execute_command(
                    f'git sparse-checkout set {self._target_path}' if self._target_path else '',
                    directory=temp_dir,
                )
            else:
                # Overwrite error to avoid reflecting the password from the URL to the output.
                stderr = ''

            if code == 0:
                # Only clone desired target folder.
                code, _, stderr = execute_command('git checkout', directory=temp_dir)

            # If checkout was successful, go on.
            if code == 0:
                # Make sure target directory exists.
                if self._target_path:
                    os.makedirs(join(temp_dir, self._target_path), exist_ok=True)
                target_file_path = join(self._target_path, file_name)
                target_file_path_full = join(temp_dir, target_file_path)

                # Write data to target file.
                with open(target_file_path_full, 'w') as f:
                    f.write(data)

                # Add changes.
                code, _, stderr = execute_command(f'git add "{target_file_path}"', directory=temp_dir)

                if code == 0:
                    # If necessary, request commit message.
                    commit_message = self._message if self._message else input('Commit message: ')

                    if not commit_message:
                        raise NoCommitMessageProvidedException(file_name)

                    # Commit changes.
                    code, _, stderr = execute_command(
                        f'git commit "{target_file_path}" -m "{commit_message}"',
                        directory=temp_dir,
                    )
                    no_changes = False

                    if code != 0:
                        if stderr.find('nothing to commit'):
                            # Everything's fine, the file just didn't change.
                            no_changes = True
                        else:
                            raise GitProblemException(f'{file_name} could not be committed to {url}', stderr)

                    if not no_changes:
                        # Push changes to repo (space before git-command to not log in history (might
                        # be disabled by the system)).
                        code, _, stderr = execute_command(
                            f' git push -u {url_with_credentials}',
                            directory=temp_dir,
                        )

                        if code != 0:
                            # Don't display Git error as it could reflect the password from the URL to the output.
                            raise GitProblemException(f'{file_name} could not be pushed to {url}')
                        
                else:
                    raise GitProblemException(f'{file_name} could not be added to Git')
            else:
                raise GitProblemException(f'Git repo {url} could not be cloned', stderr)
        return self
