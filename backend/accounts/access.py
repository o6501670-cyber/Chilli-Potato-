"""Shared centre-scope helpers used by API write paths.

The UI hides centres a user cannot access, but API callers cannot be trusted to
follow the UI. Keep the server-side rules in one small module so every write
path can enforce the same boundary.
"""

from __future__ import annotations

from typing import Any


def is_owner(user: Any) -> bool:
    """Return whether *user* has organisation-wide owner access."""
    if not user or not getattr(user, "is_authenticated", False):
        return False
    role = getattr(user, "role", None)
    role_name = getattr(role, "name", "") or ""
    return bool(getattr(user, "is_superuser", False) or role_name.lower() == "owner")


def has_global_access(user: Any) -> bool:
    """Return whether a non-owner has explicitly been granted all-centre access."""
    if is_owner(user):
        return True
    role = getattr(user, "role", None)
    permissions = getattr(role, "permissions", {}) or {}
    return permissions.get("all_centers") is True


def accessible_center_ids(user: Any) -> set[int] | None:
    """Return allowed centre IDs, or ``None`` for organisation-wide access."""
    if has_global_access(user):
        return None

    ids: set[int] = set()
    user_center_id = getattr(user, "center_id", None)
    if user_center_id:
        ids.add(int(user_center_id))

    centers = getattr(user, "centers", None)
    if centers is not None:
        ids.update(int(value) for value in centers.values_list("id", flat=True))
    return ids


def can_access_center(user: Any, center_or_id: Any) -> bool:
    """Check one centre without issuing another query when an object is given."""
    if has_global_access(user):
        return True
    center_id = getattr(center_or_id, "pk", center_or_id)
    try:
        return int(center_id) in (accessible_center_ids(user) or set())
    except (TypeError, ValueError):
        return False


def has_action_permission(user: Any, module: str, submodule: str, action: str) -> bool:
    """Read the permission shape used by the Roles screen.

    A missing permission is denied. The module fallback is intentionally
    conservative: it only grants an action when at least one configured
    submodule explicitly grants it.
    """
    if has_global_access(user):
        return True
    role = getattr(user, 'role', None)
    permissions = getattr(role, 'permissions', {}) or {}
    module_permissions = permissions.get(module)
    if not isinstance(module_permissions, dict):
        return False
    exact = module_permissions.get(submodule)
    if isinstance(exact, dict):
        return exact.get(action) is True
    # Support the legacy {access: true} / {read: true} module shape only for
    # reads. Never turn one submodule's write permission into another's.
    if action == 'read':
        return module_permissions.get('access') is True or module_permissions.get('read') is True
    return False
