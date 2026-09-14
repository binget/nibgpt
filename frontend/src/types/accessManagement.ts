export interface AdminRoleSummary {
  id: number;
  name: string;
}

export interface AdminUserScope {
  id?: number;
  scope_type: "enterprise" | "department" | "branch" | "self";
  scope_value: string | null;
  is_active?: boolean;
}

export interface AdminUser {
  id: number;
  username: string;
  full_name: string;
  email: string;
  is_active: boolean;
  roles: AdminRoleSummary[];
  scopes: AdminUserScope[];
  created_at: string | null;
}

export interface AdminUserListResponse {
  data: AdminUser[];
  count: number;
}

export interface AdminUserResponse {
  message?: string;
  data: AdminUser;
}

export interface AdminUserCreate {
  username: string;
  full_name: string;
  email: string;
  password: string;
  role_id: number;
  scopes: Array<{
    scope_type: "enterprise" | "department" | "branch" | "self";
    scope_value: string | null;
  }>;
}

export interface AdminUserUpdate {
  full_name?: string;
  email?: string;
  password?: string;
  role_id?: number;
  scopes?: Array<{
    scope_type: "enterprise" | "department" | "branch" | "self";
    scope_value: string | null;
  }>;
}

export interface AdminPermission {
  id: number;
  code: string;
  description: string | null;
  is_active: boolean;
  created_at?: string | null;
}

export interface AdminRole {
  id: number;
  name: string;
  description: string | null;
  is_active: boolean;
  permissions: AdminPermission[];
  created_at: string | null;
}

export interface AdminRoleListResponse {
  data: AdminRole[];
  count: number;
}

export interface AdminRoleCreate {
  name: string;
  description: string;
  permission_ids: number[];
}

export interface AdminRoleUpdate {
  name?: string;
  description?: string;
  is_active?: boolean;
  permission_ids?: number[];
}

export interface AdminRoleResponse {
  message?: string;
  data: AdminRole;
}

export interface AdminPermissionListResponse {
  data: AdminPermission[];
  count: number;
}
