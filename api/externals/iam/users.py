import logging
logger  = logging.getLogger(__name__)

from api.externals.http import Http
from api.externals.iam.abstract import AbstractExternalIAM
from api.models.user import User


class ExternalUsers(AbstractExternalIAM):
    @staticmethod
    def __get_users_url():
        return f"{ExternalUsers.IAM_BASE_URL}/users"

    @staticmethod
    def get_by_email(token, email):
        logger.info(f"Fetching user by email ({email})")

        url = ExternalUsers.__get_users_url() + f'/{email}'
        try:
            response = Http.get(
                url,
                token=token
            )
        except Exception as e:
            logger.warning(f"Unable to fetch user by email ({email})")
            return None

        if response.status_code == 200:
            logger.info(f"User successfully fetched by email ({email})")
            return User(
                int(response.json()['id']),
                response.json()['email']
            )
        return None

    @staticmethod
    def get_by_ids(ids):
        logger.info(f"Fetching user by ids ({ids})")
        if ids == None or len(ids) == 0:
            logger.info("No ids to fetch")
            return []

        url = ExternalUsers.__get_users_url() + f'/search'
        body = { 'userIds': ids }
        try:
            response = Http.post(
                url,
                body=body
            )
        except Exception as e:
            logger.warning(f"Unable to fetch user by ids ({ids})", e)
            return []

        if response.status_code == 200:
            response_content = response.json()
            return [
                User(int(data['id']), data['email']) for data in response_content
            ]
        return []

    @staticmethod
    def fill_workspaces_users(workspaces):
        userIds = []
        for workspace in workspaces:
            userIds = list(set(userIds + workspace.users))

        users = ExternalUsers.get_by_ids(userIds)
        for workspace in workspaces:
            for i, userId in enumerate(workspace.users):
                user = [ user for user in users if user.id == userId ]
                if user:
                    workspace.users[i] = user[0]

        return workspaces

    @staticmethod
    def fill_workspace_users(workspace):
        return ExternalUsers.fill_workspaces_users([workspace])[0]

