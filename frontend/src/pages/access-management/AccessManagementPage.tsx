import { AddOutlined, EditOutlined, LockOutlined, LockOpenOutlined, SearchOutlined, } from "@mui/icons-material";
import { Alert, Box, Button, Chip, CircularProgress, Dialog, DialogActions, DialogContent, DialogTitle, FormControl, IconButton, InputAdornment, InputLabel, MenuItem, Paper, Select, Stack, Tab, Tabs, TextField, Tooltip, Typography, Checkbox, } from "@mui/material";
import { useEffect, useMemo, useState } from "react";
import { createAdminRole, createAdminUser, getAdminPermissions, getAdminRoles, getAdminUsers, updateAdminRole, updateAdminUser, updateAdminUserStatus,createAdminPermission,
updateAdminPermission, } from "../../services/accessManagement";
import type { AdminPermission, AdminRole, AdminRoleCreate, AdminRoleUpdate, AdminUser, AdminUserCreate, AdminUserScope, AdminUserUpdate, AdminPermissionCreate,
AdminPermissionUpdate, } from "../../types/accessManagement";
type ScopeType = "enterprise" | "department" | "branch" | "self";
interface UserFormState {
    username: string;
    full_name: string;
    email: string;
    password: string;
    role_id: string;
    scope_type: ScopeType;
    scope_value: string;
}
const emptyUserForm: UserFormState = {
    username: "",
    full_name: "",
    email: "",
    password: "",
    role_id: "",
    scope_type: "enterprise",
    scope_value: "",
};
interface RoleFormState {
    name: string;
    description: string;
    permission_ids: number[];
}
const emptyRoleForm: RoleFormState = {
    name: "",
    description: "",
    permission_ids: [],
};

interface PermissionFormState {
  code: string;
  description: string;
}

const emptyPermissionForm: PermissionFormState = {
  code: "",
  description: "",
};


function AccessManagementPage() {
    const [tab, setTab] = useState(0);
    const [users, setUsers] = useState<AdminUser[]>([]);
    const [roles, setRoles] = useState<AdminRole[]>([]);
    const [permissions, setPermissions] = useState<AdminPermission[]>([]);
    const [roleDialogOpen, setRoleDialogOpen] = useState(false);
    const [editingRole, setEditingRole] = useState<AdminRole | null>(null);
    const [roleForm, setRoleForm] = useState<RoleFormState>(emptyRoleForm);
    const [permissionsLoading, setPermissionsLoading] = useState(false);
    const [permissionDialogOpen, setPermissionDialogOpen] =
  useState(false);

const [editingPermission, setEditingPermission] =
  useState<AdminPermission | null>(null);

const [permissionForm, setPermissionForm] =
  useState<PermissionFormState>(emptyPermissionForm);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState("");
    const [success, setSuccess] = useState("");
    const [search, setSearch] = useState("");
    const [dialogOpen, setDialogOpen] = useState(false);
    const [editingUser, setEditingUser] = useState<AdminUser | null>(null);
    const [form, setForm] = useState<UserFormState>(emptyUserForm);
    async function loadData() {
        setLoading(true);
        setError("");
        try {
            const [usersResponse, rolesResponse] = await Promise.all([
                getAdminUsers(),
                getAdminRoles(),
            ]);
            setUsers(usersResponse.data);
            setRoles(rolesResponse.data);
        }
        catch (err: any) {
            setError(err?.response?.data?.detail ||
                "Unable to load access management data.");
        }
        finally {
            setLoading(false);
        }
    }
    useEffect(() => {
        loadData();
    }, []);
    useEffect(() => {
        if (
          (tab !== 1 && tab !== 2) ||
          permissions.length > 0
        ) {
          return;
        }
        async function loadPermissions() {
            setPermissionsLoading(true);
            setError("");
            try {
                const response = await getAdminPermissions();
                setPermissions(response.data);
            }
            catch (err: any) {
                setError(err?.response?.data?.detail ||
                    "Unable to load permissions.");
            }
            finally {
                setPermissionsLoading(false);
            }
        }
        loadPermissions();
    }, [tab, permissions.length]);
    const filteredUsers = useMemo(() => {
        const value = search.trim().toLowerCase();
        if (!value) {
            return users;
        }
        return users.filter((user) => {
            const roleNames = user.roles
                .map((role) => role.name)
                .join(" ");
            const scopes = user.scopes
                .map((scope) => `${scope.scope_type} ${scope.scope_value ?? ""}`)
                .join(" ");
            return [
                user.full_name,
                user.username,
                user.email,
                roleNames,
                scopes,
            ]
                .join(" ")
                .toLowerCase()
                .includes(value);
        });
    }, [search, users]);
    function openCreateDialog() {
        setEditingUser(null);
        setForm(emptyUserForm);
        setError("");
        setSuccess("");
        setDialogOpen(true);
    }
    function openEditDialog(user: AdminUser) {
        const firstRole = user.roles[0];
        const firstScope = user.scopes.find((scope) => scope.is_active !== false) || user.scopes[0];
        setEditingUser(user);
        setForm({
            username: user.username,
            full_name: user.full_name,
            email: user.email,
            password: "",
            role_id: firstRole
                ? String(firstRole.id)
                : "",
            scope_type: firstScope?.scope_type || "enterprise",
            scope_value: firstScope?.scope_value || "",
        });
        setError("");
        setSuccess("");
        setDialogOpen(true);
    }
    function buildScopes(): Array<{
        scope_type: ScopeType;
        scope_value: string | null;
    }> {
        if (form.scope_type === "enterprise" ||
            form.scope_type === "self") {
            return [
                {
                    scope_type: form.scope_type,
                    scope_value: null,
                },
            ];
        }
        return [
            {
                scope_type: form.scope_type,
                scope_value: form.scope_value.trim() || null,
            },
        ];
    }
    async function handleSaveUser() {
        setSaving(true);
        setError("");
        setSuccess("");
        try {
            if (!form.role_id) {
                setError("Please select a role.");
                return;
            }
            if (["branch", "department"].includes(form.scope_type) &&
                !form.scope_value.trim()) {
                setError(`${form.scope_type} scope requires a value.`);
                return;
            }
            if (editingUser) {
                const payload: AdminUserUpdate = {
                    full_name: form.full_name.trim(),
                    email: form.email.trim(),
                    role_id: Number(form.role_id),
                    scopes: buildScopes(),
                };
                if (form.password.trim()) {
                    payload.password = form.password;
                }
                await updateAdminUser(editingUser.id, payload);
                setSuccess("User updated successfully.");
            }
            else {
                const payload: AdminUserCreate = {
                    username: form.username.trim(),
                    full_name: form.full_name.trim(),
                    email: form.email.trim(),
                    password: form.password,
                    role_id: Number(form.role_id),
                    scopes: buildScopes(),
                };
                await createAdminUser(payload);
                setSuccess("User created successfully.");
            }
            setDialogOpen(false);
            await loadData();
        }
        catch (err: any) {
            setError(err?.response?.data?.detail ||
                "Unable to save user.");
        }
        finally {
            setSaving(false);
        }
    }
    async function handleStatusChange(user: AdminUser) {
        const action = user.is_active
            ? "disable"
            : "activate";
        const confirmed = window.confirm(`Are you sure you want to ${action} ${user.username}?`);
        if (!confirmed) {
            return;
        }
        setError("");
        setSuccess("");
        try {
            await updateAdminUserStatus(user.id, !user.is_active);
            setSuccess(user.is_active
                ? "User disabled successfully."
                : "User activated successfully.");
            await loadData();
        }
        catch (err: any) {
            setError(err?.response?.data?.detail ||
                `Unable to ${action} user.`);
        }
    }
    function formatScopes(scopes: AdminUserScope[]) {
        const activeScopes = scopes.filter((scope) => scope.is_active !== false);
        if (!activeScopes.length) {
            return "No scope";
        }
        return activeScopes
            .map((scope) => {
            if (scope.scope_value) {
                return `${scope.scope_type}: ${scope.scope_value}`;
            }
            return scope.scope_type;
        })
            .join(", ");
    }
    function openCreateRoleDialog() {
        setEditingRole(null);
        setRoleForm(emptyRoleForm);
        setError("");
        setSuccess("");
        setRoleDialogOpen(true);
    }
    function openEditRoleDialog(role: AdminRole) {
        setEditingRole(role);
        setRoleForm({
            name: role.name,
            description: role.description || "",
            permission_ids: role.permissions.map((permission) => permission.id),
        });
        setError("");
        setSuccess("");
        setRoleDialogOpen(true);
    }
    function toggleRolePermission(permissionId: number) {
        setRoleForm((current) => {
            const exists = current.permission_ids.includes(permissionId);
            return {
                ...current,
                permission_ids: exists
                    ? current.permission_ids.filter((id) => id !== permissionId)
                    : [
                        ...current.permission_ids,
                        permissionId,
                    ],
            };
        });
    }
    async function handleSaveRole() {
        setSaving(true);
        setError("");
        setSuccess("");
        try {
            if (!roleForm.name.trim()) {
                setError("Role name is required.");
                return;
            }
            if (editingRole) {
                const payload: AdminRoleUpdate = {
                    name: roleForm.name.trim(),
                    description: roleForm.description.trim(),
                    permission_ids: roleForm.permission_ids,
                };
                await updateAdminRole(editingRole.id, payload);
                setSuccess("Role updated successfully.");
            }
            else {
                const payload: AdminRoleCreate = {
                    name: roleForm.name.trim(),
                    description: roleForm.description.trim(),
                    permission_ids: roleForm.permission_ids,
                };
                await createAdminRole(payload);
                setSuccess("Role created successfully.");
            }
            setRoleDialogOpen(false);
            await loadData();
        }
        catch (err: any) {
            setError(err?.response?.data?.detail ||
                "Unable to save role.");
        }
        finally {
            setSaving(false);
        }
    }
    async function handleRoleStatusChange(role: AdminRole) {
        const action = role.is_active
            ? "disable"
            : "activate";
        if (role.name.toLowerCase() === "admin" &&
            role.is_active) {
            setError("The administrator role cannot be disabled.");
            return;
        }
        const confirmed = window.confirm(`Are you sure you want to ${action} the ${role.name} role?`);
        if (!confirmed) {
            return;
        }
        setError("");
        setSuccess("");
        try {
            await updateAdminRole(role.id, {
                is_active: !role.is_active,
            });
            setSuccess(role.is_active
                ? "Role disabled successfully."
                : "Role activated successfully.");
            await loadData();
        }
        catch (err: any) {
            setError(err?.response?.data?.detail ||
                `Unable to ${action} role.`);
        }
    }

    function openCreatePermissionDialog() {
  setEditingPermission(null);
  setPermissionForm(emptyPermissionForm);
  setError("");
  setSuccess("");
  setPermissionDialogOpen(true);
}

function openEditPermissionDialog(
  permission: AdminPermission
) {
  setEditingPermission(permission);

  setPermissionForm({
    code: permission.code,
    description: permission.description || "",
  });

  setError("");
  setSuccess("");
  setPermissionDialogOpen(true);
}

async function refreshPermissions() {
  const response = await getAdminPermissions();
  setPermissions(response.data);
}

async function handleSavePermission() {
  setSaving(true);
  setError("");
  setSuccess("");

  try {
    if (!permissionForm.code.trim()) {
      setError("Permission code is required.");
      return;
    }

    if (editingPermission) {
      const payload: AdminPermissionUpdate = {
        code: permissionForm.code.trim(),
        description:
          permissionForm.description.trim(),
      };

      await updateAdminPermission(
        editingPermission.id,
        payload
      );

      setSuccess(
        "Permission updated successfully."
      );
    } else {
      const payload: AdminPermissionCreate = {
        code: permissionForm.code.trim(),
        description:
          permissionForm.description.trim(),
      };

      await createAdminPermission(payload);

      setSuccess(
        "Permission created successfully."
      );
    }

    setPermissionDialogOpen(false);
    await refreshPermissions();
  } catch (err: any) {
    setError(
      err?.response?.data?.detail ||
        "Unable to save permission."
    );
  } finally {
    setSaving(false);
  }
}

async function handlePermissionStatusChange(
  permission: AdminPermission
) {
  const action = permission.is_active
    ? "disable"
    : "activate";

  if (
    permission.code ===
      "admin.permissions.manage" &&
    permission.is_active
  ) {
    setError(
      "admin.permissions.manage cannot be disabled."
    );
    return;
  }

  const confirmed = window.confirm(
    `Are you sure you want to ${action} ${permission.code}?`
  );

  if (!confirmed) {
    return;
  }

  setError("");
  setSuccess("");

  try {
    await updateAdminPermission(
      permission.id,
      {
        is_active: !permission.is_active,
      }
    );

    setSuccess(
      permission.is_active
        ? "Permission disabled successfully."
        : "Permission activated successfully."
    );

    await refreshPermissions();
  } catch (err: any) {
    setError(
      err?.response?.data?.detail ||
        `Unable to ${action} permission.`
    );
  }
}

    return ( 
    <Box>
      <Stack direction={{
            xs: "column",
            md: "row",
        }} justifyContent="space-between" alignItems={{
            xs: "flex-start",
            md: "center",
        }} spacing={2} sx={{ mb: 3 }}>
        <Box>
          <Typography variant="h4" sx={{
            fontWeight: 900,
            color: "#3d2315",
        }}>
            Access Management
          </Typography>

          <Typography variant="body2" sx={{
            mt: 0.5,
            color: "text.secondary",
        }}>
            Manage NIBGPT users, roles,
            permissions and governed data access.
          </Typography>
        </Box>

        {(tab === 0 || tab === 1 || tab === 2) && (<Button variant="contained" startIcon={<AddOutlined />} onClick={
  tab === 0
    ? openCreateDialog
    : tab === 1
      ? openCreateRoleDialog
      : openCreatePermissionDialog
} sx={{
                bgcolor: "#5b311b",
                "&:hover": {
                    bgcolor: "#472512",
                },
            }}>
          {tab === 0
  ? "Create User"
  : tab === 1
    ? "Create Role"
    : "Create Permission"}
        </Button>)}
      </Stack>


      {error && (<Alert severity="error" sx={{ mb: 2 }} onClose={() => setError("")}>
          {String(error)}
        </Alert>)}

      {success && (<Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess("")}>
          {success}
        </Alert>)}


      <Paper elevation={0} sx={{
            border: "1px solid",
            borderColor: "divider",
            borderRadius: 3,
            overflow: "hidden",
        }}>
        <Tabs value={tab} onChange={(_, value) => setTab(value)} sx={{
            px: 2,
            borderBottom: "1px solid",
            borderColor: "divider",
            "& .MuiTab-root": {
                fontWeight: 700,
            },
            "& .Mui-selected": {
                color: "#5b311b !important",
            },
            "& .MuiTabs-indicator": {
                bgcolor: "#d9a438",
            },
        }}>
          <Tab label="Users"/>
          <Tab label="Roles"/>
          <Tab label="Permissions"/>
        </Tabs>


        {tab === 0 && (<Box sx={{ p: 3 }}>
            <TextField fullWidth size="small" placeholder="Search by name, username, email, role or scope..." value={search} onChange={(event) => setSearch(event.target.value)} slotProps={{
                input: {
                    startAdornment: (<InputAdornment position="start">
                      <SearchOutlined />
                    </InputAdornment>),
                },
            }} sx={{ mb: 3 }}/>


            {loading ? (<Box sx={{
                    py: 8,
                    display: "flex",
                    justifyContent: "center",
                }}>
                <CircularProgress />
              </Box>) : (<Box sx={{
                    overflowX: "auto",
                }}>
                <Box component="table" sx={{
                    width: "100%",
                    borderCollapse: "collapse",
                    minWidth: 900,
                    "& th": {
                        textAlign: "left",
                        py: 1.5,
                        px: 2,
                        fontSize: "0.78rem",
                        textTransform: "uppercase",
                        letterSpacing: "0.04em",
                        color: "text.secondary",
                        borderBottom: "1px solid",
                        borderColor: "divider",
                    },
                    "& td": {
                        py: 1.6,
                        px: 2,
                        borderBottom: "1px solid",
                        borderColor: "divider",
                        verticalAlign: "middle",
                    },
                }}>
                  <Box component="thead">
                    <Box component="tr">
                      <Box component="th">
                        User
                      </Box>
                      <Box component="th">
                        Role
                      </Box>
                      <Box component="th">
                        Data Scope
                      </Box>
                      <Box component="th">
                        Status
                      </Box>
                      <Box component="th" sx={{
                    width: 110,
                    textAlign: "right !important",
                }}>
                        Actions
                      </Box>
                    </Box>
                  </Box>

                  <Box component="tbody">
                    {filteredUsers.map((user) => (<Box component="tr" key={user.id}>
                          <Box component="td">
                            <Typography sx={{
                        fontWeight: 700,
                        color: "#3d2315",
                    }}>
                              {user.full_name}
                            </Typography>

                            <Typography variant="caption" color="text.secondary">
                              {user.username}
                              {" · "}
                              {user.email}
                            </Typography>
                          </Box>

                          <Box component="td">
                            <Stack direction="row" spacing={0.7} flexWrap="wrap" useFlexGap>
                              {user.roles.length ? (user.roles.map((role) => (<Chip key={role.id} label={role.name} size="small" sx={{
                            fontWeight: 700,
                        }}/>))) : (<Chip label="No role" size="small" variant="outlined"/>)}
                            </Stack>
                          </Box>

                          <Box component="td">
                            <Typography variant="body2" sx={{
                        textTransform: "capitalize",
                    }}>
                              {formatScopes(user.scopes)}
                            </Typography>
                          </Box>

                          <Box component="td">
                            <Chip label={user.is_active
                        ? "Active"
                        : "Disabled"} size="small" color={user.is_active
                        ? "success"
                        : "default"}/>
                          </Box>

                          <Box component="td" sx={{
                        textAlign: "right",
                    }}>
                            <Tooltip title="Edit user">
                              <IconButton size="small" onClick={() => openEditDialog(user)}>
                                <EditOutlined fontSize="small"/>
                              </IconButton>
                            </Tooltip>

                            <Tooltip title={user.is_active
                        ? "Disable user"
                        : "Activate user"}>
                              <IconButton size="small" onClick={() => handleStatusChange(user)}>
                                {user.is_active ? (<LockOutlined fontSize="small"/>) : (<LockOpenOutlined fontSize="small"/>)}
                              </IconButton>
                            </Tooltip>
                          </Box>
                        </Box>))}

                    {!filteredUsers.length && (<Box component="tr">
                        <Box component="td" colSpan={5} sx={{
                        textAlign: "center",
                        py: "48px !important",
                        color: "text.secondary",
                    }}>
                          No users found.
                        </Box>
                      </Box>)}
                  </Box>
                </Box>
              </Box>)}
          </Box>)}


        {tab === 1 && (<Box sx={{ p: 3 }}>
    {loading ? (<Box sx={{
                    py: 8,
                    display: "flex",
                    justifyContent: "center",
                }}>
        <CircularProgress />
      </Box>) : (<Box sx={{ overflowX: "auto" }}>
        <Box component="table" sx={{
                    width: "100%",
                    borderCollapse: "collapse",
                    minWidth: 850,
                    "& th": {
                        textAlign: "left",
                        py: 1.5,
                        px: 2,
                        fontSize: "0.78rem",
                        textTransform: "uppercase",
                        letterSpacing: "0.04em",
                        color: "text.secondary",
                        borderBottom: "1px solid",
                        borderColor: "divider",
                    },
                    "& td": {
                        py: 1.6,
                        px: 2,
                        borderBottom: "1px solid",
                        borderColor: "divider",
                        verticalAlign: "middle",
                    },
                }}>
          <Box component="thead">
            <Box component="tr">
              <Box component="th">
                Role
              </Box>

              <Box component="th">
                Permissions
              </Box>

              <Box component="th">
                Status
              </Box>

              <Box component="th" sx={{
                    width: 110,
                    textAlign: "right !important",
                }}>
                Actions
              </Box>
            </Box>
          </Box>

          <Box component="tbody">
            {roles.map((role) => (<Box component="tr" key={role.id}>
                <Box component="td">
                  <Typography sx={{
                        fontWeight: 700,
                        color: "#3d2315",
                    }}>
                    {role.name}
                  </Typography>

                  <Typography variant="caption" color="text.secondary">
                    {role.description ||
                        "No description"}
                  </Typography>
                </Box>

                <Box component="td">
                  <Stack direction="row" spacing={0.7} flexWrap="wrap" useFlexGap>
                    {role.permissions.length ? (<>
                        {role.permissions
                            .slice(0, 4)
                            .map((permission) => (<Chip key={permission.id} label={permission.code} size="small" variant="outlined"/>))}

                        {role.permissions.length >
                            4 && (<Chip label={`+${role.permissions
                                .length - 4} more`} size="small"/>)}
                      </>) : (<Chip label="No permissions" size="small" variant="outlined"/>)}
                  </Stack>
                </Box>

                <Box component="td">
                  <Chip label={role.is_active
                        ? "Active"
                        : "Disabled"} size="small" color={role.is_active
                        ? "success"
                        : "default"}/>
                </Box>

                <Box component="td" sx={{
                        textAlign: "right",
                    }}>
                  <Tooltip title="Edit role">
                    <IconButton size="small" onClick={() => openEditRoleDialog(role)}>
                      <EditOutlined fontSize="small"/>
                    </IconButton>
                  </Tooltip>

                  <Tooltip title={role.name.toLowerCase() ===
                        "admin" &&
                        role.is_active
                        ? "Admin role cannot be disabled"
                        : role.is_active
                            ? "Disable role"
                            : "Activate role"}>
                    <span>
                      <IconButton size="small" disabled={role.name.toLowerCase() ===
                        "admin" &&
                        role.is_active} onClick={() => handleRoleStatusChange(role)}>
                        {role.is_active ? (<LockOutlined fontSize="small"/>) : (<LockOpenOutlined fontSize="small"/>)}
                      </IconButton>
                    </span>
                  </Tooltip>
                </Box>
              </Box>))}

            {!roles.length && (<Box component="tr">
                <Box component="td" colSpan={4} sx={{
                        textAlign: "center",
                        py: "48px !important",
                        color: "text.secondary",
                    }}>
                  No roles found.
                </Box>
              </Box>)}
          </Box>
        </Box>
      </Box>)}
  </Box>)}


        {tab === 2 && (
  <Box sx={{ p: 3 }}>
    {permissionsLoading ? (
      <Box
        sx={{
          py: 8,
          display: "flex",
          justifyContent: "center",
        }}
      >
        <CircularProgress />
      </Box>
    ) : (
      <Box sx={{ overflowX: "auto" }}>
        <Box
          component="table"
          sx={{
            width: "100%",
            borderCollapse: "collapse",
            minWidth: 800,
            "& th": {
              textAlign: "left",
              py: 1.5,
              px: 2,
              fontSize: "0.78rem",
              textTransform: "uppercase",
              letterSpacing: "0.04em",
              color: "text.secondary",
              borderBottom: "1px solid",
              borderColor: "divider",
            },
            "& td": {
              py: 1.6,
              px: 2,
              borderBottom: "1px solid",
              borderColor: "divider",
              verticalAlign: "middle",
            },
          }}
        >
          <Box component="thead">
            <Box component="tr">
              <Box component="th">
                Permission
              </Box>

              <Box component="th">
                Description
              </Box>

              <Box component="th">
                Status
              </Box>

              <Box
                component="th"
                sx={{
                  width: 110,
                  textAlign:
                    "right !important",
                }}
              >
                Actions
              </Box>
            </Box>
          </Box>

          <Box component="tbody">
            {permissions.map(
              (permission) => (
                <Box
                  component="tr"
                  key={permission.id}
                >
                  <Box component="td">
                    <Typography
                      sx={{
                        fontWeight: 700,
                        color: "#3d2315",
                      }}
                    >
                      {permission.code}
                    </Typography>
                  </Box>

                  <Box component="td">
                    <Typography
                      variant="body2"
                      color="text.secondary"
                    >
                      {permission.description ||
                        "No description"}
                    </Typography>
                  </Box>

                  <Box component="td">
                    <Chip
                      label={
                        permission.is_active
                          ? "Active"
                          : "Disabled"
                      }
                      size="small"
                      color={
                        permission.is_active
                          ? "success"
                          : "default"
                      }
                    />
                  </Box>

                  <Box
                    component="td"
                    sx={{
                      textAlign: "right",
                    }}
                  >
                    <Tooltip title="Edit permission">
                      <IconButton
                        size="small"
                        onClick={() =>
                          openEditPermissionDialog(
                            permission
                          )
                        }
                      >
                        <EditOutlined fontSize="small" />
                      </IconButton>
                    </Tooltip>

                    <Tooltip
                      title={
                        permission.code ===
                          "admin.permissions.manage" &&
                        permission.is_active
                          ? "Protected permission"
                          : permission.is_active
                            ? "Disable permission"
                            : "Activate permission"
                      }
                    >
                      <span>
                        <IconButton
                          size="small"
                          disabled={
                            permission.code ===
                              "admin.permissions.manage" &&
                            permission.is_active
                          }
                          onClick={() =>
                            handlePermissionStatusChange(
                              permission
                            )
                          }
                        >
                          {permission.is_active ? (
                            <LockOutlined fontSize="small" />
                          ) : (
                            <LockOpenOutlined fontSize="small" />
                          )}
                        </IconButton>
                      </span>
                    </Tooltip>
                  </Box>
                </Box>
              )
            )}

            {!permissions.length && (
              <Box component="tr">
                <Box
                  component="td"
                  colSpan={4}
                  sx={{
                    textAlign: "center",
                    py: "48px !important",
                    color: "text.secondary",
                  }}
                >
                  No permissions found.
                </Box>
              </Box>
            )}
          </Box>
        </Box>
      </Box>
    )}
  </Box>
)}
      </Paper>


      <Dialog open={dialogOpen} onClose={() => !saving &&
            setDialogOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle sx={{
            fontWeight: 800,
            color: "#3d2315",
        }}>
          {editingUser
            ? "Edit User"
            : "Create User"}
        </DialogTitle>

        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField label="Username" value={form.username} disabled={Boolean(editingUser)} onChange={(event) => setForm({
            ...form,
            username: event.target.value,
        })} required/>

            <TextField label="Full Name" value={form.full_name} onChange={(event) => setForm({
            ...form,
            full_name: event.target.value,
        })} required/>

            <TextField label="Email" type="email" value={form.email} onChange={(event) => setForm({
            ...form,
            email: event.target.value,
        })} required/>

            <TextField label={editingUser
            ? "New Password (optional)"
            : "Password"} type="password" value={form.password} onChange={(event) => setForm({
            ...form,
            password: event.target.value,
        })} required={!editingUser} helperText={editingUser
            ? "Leave blank to keep the existing password."
            : "Minimum 8 characters."}/>

            <FormControl required>
              <InputLabel>
                Role
              </InputLabel>

              <Select label="Role" value={form.role_id} onChange={(event) => setForm({
            ...form,
            role_id: event.target.value,
        })}>
                {roles
            .filter((role) => role.is_active)
            .map((role) => (<MenuItem key={role.id} value={String(role.id)}>
                      {role.name}
                    </MenuItem>))}
              </Select>
            </FormControl>

            <FormControl required>
              <InputLabel>
                Data Scope
              </InputLabel>

              <Select label="Data Scope" value={form.scope_type} onChange={(event) => setForm({
            ...form,
            scope_type: event.target
                .value as ScopeType,
            scope_value: "",
        })}>
                <MenuItem value="enterprise">
                  Enterprise
                </MenuItem>

                <MenuItem value="department">
                  Department
                </MenuItem>

                <MenuItem value="branch">
                  Branch
                </MenuItem>

                <MenuItem value="self">
                  Self
                </MenuItem>
              </Select>
            </FormControl>

            {(form.scope_type ===
            "branch" ||
            form.scope_type ===
                "department") && (<TextField label={form.scope_type ===
                "branch"
                ? "Branch Code"
                : "Department"} value={form.scope_value} onChange={(event) => setForm({
                ...form,
                scope_value: event.target.value,
            })} required/>)}
          </Stack>
        </DialogContent>

        <DialogActions sx={{
            px: 3,
            pb: 3,
        }}>
          <Button onClick={() => setDialogOpen(false)} disabled={saving}>
            Cancel
          </Button>

          <Button variant="contained" onClick={handleSaveUser} disabled={saving} sx={{
            bgcolor: "#5b311b",
            "&:hover": {
                bgcolor: "#472512",
            },
        }}>
            {saving
            ? "Saving..."
            : editingUser
                ? "Save Changes"
                : "Create User"}
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={roleDialogOpen} onClose={() => !saving &&
            setRoleDialogOpen(false)} fullWidth maxWidth="md">
  <DialogTitle sx={{
            fontWeight: 800,
            color: "#3d2315",
        }}>
    {editingRole
            ? "Edit Role"
            : "Create Role"}
  </DialogTitle>

  <DialogContent>
    <Stack spacing={2.5} sx={{ mt: 1 }}>
      <TextField label="Role Name" value={roleForm.name} onChange={(event) => setRoleForm({
            ...roleForm,
            name: event.target.value,
        })} required/>

      <TextField label="Description" value={roleForm.description} onChange={(event) => setRoleForm({
            ...roleForm,
            description: event.target.value,
        })} multiline minRows={2}/>

      <Box>
        <Typography sx={{
            fontWeight: 800,
            mb: 1,
            color: "#3d2315",
        }}>
          Permissions
        </Typography>

        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Select the actions users with
          this role are authorized to
          perform.
        </Typography>

        {permissionsLoading ? (<Box sx={{
                py: 4,
                display: "flex",
                justifyContent: "center",
            }}>
            <CircularProgress size={28}/>
          </Box>) : (<Box sx={{
                border: "1px solid",
                borderColor: "divider",
                borderRadius: 2,
                maxHeight: 360,
                overflowY: "auto",
            }}>
            {permissions
                .filter((permission) => permission.is_active)
                .map((permission) => (<Box key={permission.id} sx={{
                    display: "flex",
                    alignItems: "flex-start",
                    px: 2,
                    py: 1.2,
                    borderBottom: "1px solid",
                    borderColor: "divider",
                    "&:last-child": {
                        borderBottom: "none",
                    },
                }}>
                  <Checkbox checked={roleForm.permission_ids.includes(permission.id)} onChange={() => toggleRolePermission(permission.id)} sx={{
                    mt: -0.8,
                    color: "#b77b24",
                    "&.Mui-checked": {
                        color: "#5b311b",
                    },
                }}/>

                  <Box>
                    <Typography sx={{
                    fontWeight: 700,
                    fontSize: "0.9rem",
                }}>
                      {permission.code}
                    </Typography>

                    {permission.description && (<Typography variant="caption" color="text.secondary">
                        {permission.description}
                      </Typography>)}
                  </Box>
                </Box>))}
          </Box>)}

        <Typography variant="caption" color="text.secondary" sx={{
            display: "block",
            mt: 1,
        }}>
          {roleForm.permission_ids
            .length}{" "}
          permission(s) selected
        </Typography>
      </Box>
    </Stack>
  </DialogContent>

  <DialogActions sx={{
            px: 3,
            pb: 3,
        }}>
    <Button onClick={() => setRoleDialogOpen(false)} disabled={saving}>
      Cancel
    </Button>

    <Button variant="contained" onClick={handleSaveRole} disabled={saving ||
            permissionsLoading} sx={{
            bgcolor: "#5b311b",
            "&:hover": {
                bgcolor: "#472512",
            },
        }}>
      {saving
            ? "Saving..."
            : editingRole
                ? "Save Changes"
                : "Create Role"}
    </Button>
  </DialogActions>
    </Dialog>

    <Dialog
  open={permissionDialogOpen}
  onClose={() =>
    !saving &&
    setPermissionDialogOpen(false)
  }
  fullWidth
  maxWidth="sm"
>
  <DialogTitle
    sx={{
      fontWeight: 800,
      color: "#3d2315",
    }}
  >
    {editingPermission
      ? "Edit Permission"
      : "Create Permission"}
  </DialogTitle>

  <DialogContent>
    <Stack spacing={2.5} sx={{ mt: 1 }}>
      <TextField
        label="Permission Code"
        value={permissionForm.code}
        onChange={(event) =>
          setPermissionForm({
            ...permissionForm,
            code: event.target.value,
          })
        }
        placeholder="example.feature.view"
        required
      />

      <TextField
        label="Description"
        value={permissionForm.description}
        onChange={(event) =>
          setPermissionForm({
            ...permissionForm,
            description:
              event.target.value,
          })
        }
        multiline
        minRows={3}
      />
    </Stack>
  </DialogContent>

  <DialogActions
    sx={{
      px: 3,
      pb: 3,
    }}
  >
    <Button
      onClick={() =>
        setPermissionDialogOpen(false)
      }
      disabled={saving}
    >
      Cancel
    </Button>

    <Button
      variant="contained"
      onClick={handleSavePermission}
      disabled={saving}
      sx={{
        bgcolor: "#5b311b",
        "&:hover": {
          bgcolor: "#472512",
        },
      }}
    >
      {saving
        ? "Saving..."
        : editingPermission
          ? "Save Changes"
          : "Create Permission"}
    </Button>
  </DialogActions>
</Dialog>
    </Box>);
}
export default AccessManagementPage;