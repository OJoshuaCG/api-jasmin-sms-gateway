from fastapi import APIRouter

from app.controllers.groups_controller import GroupsController
from app.schemas.groups import GroupCreate, GroupOut, GroupUpdate
from app.utils.response import ApiResponse, empty, success

router = APIRouter(prefix="/groups", tags=["Groups"])


@router.get("/", response_model=ApiResponse[list[GroupOut]], summary="List all groups")
async def list_groups():
    """
    Returns all Jasmin groups.

    Groups are permission containers. Users are assigned to exactly one group.
    Disabling a group blocks all users in it from sending MT messages.

    **Response fields:**
    - `gid` — unique group identifier
    - `enabled` — whether the group is active
    """
    return success(data=await GroupsController().list_groups())


@router.get("/{gid}", response_model=ApiResponse[GroupOut], summary="Get a group")
async def get_group(gid: str):
    """
    Returns a single group by its ID.

    **Path parameter:**
    - `gid` — group identifier (e.g. `premium_customers`)

    Returns **404** if the group does not exist.
    """
    return success(data=await GroupsController().get_group(gid))


@router.post("/", response_model=ApiResponse[GroupOut], status_code=201, summary="Create a group")
async def create_group(body: GroupCreate):
    """
    Creates a new Jasmin group.

    **Body:**
    ```json
    { "gid": "premium_customers" }
    ```

    - `gid` must be unique, 1–64 characters, no spaces.

    Returns **409** if a group with the same `gid` already exists.

    Configuration is automatically persisted to disk after creation.
    """
    return success(data=await GroupsController().create_group(body), message="Group created")


@router.patch("/{gid}", response_model=ApiResponse[GroupOut], summary="Enable or disable a group")
async def update_group(gid: str, body: GroupUpdate):
    """
    Enables or disables a Jasmin group.

    **Body:**
    ```json
    { "enabled": false }
    ```

    Disabling a group immediately blocks all users in it from submitting MT messages.
    Enabling it restores their access without needing to recreate them.

    Returns **404** if the group does not exist.
    """
    return success(data=await GroupsController().update_group(gid, body))


@router.delete("/{gid}", response_model=ApiResponse[None], summary="Delete a group")
async def delete_group(gid: str):
    """
    Deletes a Jasmin group.

    **Path parameter:**
    - `gid` — group identifier to delete

    Returns **404** if the group does not exist.

    > **Warning:** Deleting a group that has active users will leave those users without
    > a valid group assignment. Remove or reassign users before deleting their group.

    Configuration is automatically persisted to disk after deletion.
    """
    await GroupsController().delete_group(gid)
    return empty("Group deleted")
