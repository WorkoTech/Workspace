from enum import Enum


class WorkspacePermission(Enum):
    """
    Define user workspace permissions from IAM
    """
    CREATOR = "CREATOR"
    USER = "USER"
    REFERENT = "REFERENT"
    NONE = "NONE"
