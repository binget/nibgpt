import api from "./api";

import type {
  AdminRoleListResponse,
  AdminUserCreate,
  AdminUserListResponse,
  AdminUserResponse,
  AdminUserUpdate,
  AdminPermissionListResponse,
AdminRoleCreate,
AdminRoleResponse,
AdminRoleUpdate,
AdminPermissionCreate,
AdminPermissionResponse,
AdminPermissionUpdate,
} from "../types/accessManagement";


export async function getAdminUsers(): Promise<AdminUserListResponse> {
  const response = await api.get<AdminUserListResponse>(
    "/api/admin/users"
  );

  return response.data;
}


export async function getAdminRoles(): Promise<AdminRoleListResponse> {
  const response = await api.get<AdminRoleListResponse>(
    "/api/admin/roles"
  );

  return response.data;
}


export async function createAdminUser(
  payload: AdminUserCreate
): Promise<AdminUserResponse> {
  const response = await api.post<AdminUserResponse>(
    "/api/admin/users",
    payload
  );

  return response.data;
}


export async function updateAdminUser(
  userId: number,
  payload: AdminUserUpdate
): Promise<AdminUserResponse> {
  const response = await api.put<AdminUserResponse>(
    `/api/admin/users/${userId}`,
    payload
  );

  return response.data;
}


export async function updateAdminUserStatus(
  userId: number,
  isActive: boolean
): Promise<AdminUserResponse> {
  const response = await api.patch<AdminUserResponse>(
    `/api/admin/users/${userId}/status`,
    {
      is_active: isActive,
    }
  );

  return response.data;
}

export async function getAdminPermissions(): Promise<AdminPermissionListResponse> {
  const response = await api.get<AdminPermissionListResponse>(
    "/api/admin/permissions"
  );

  return response.data;
}


export async function createAdminRole(
  payload: AdminRoleCreate
): Promise<AdminRoleResponse> {
  const response = await api.post<AdminRoleResponse>(
    "/api/admin/roles",
    payload
  );

  return response.data;
}


export async function updateAdminRole(
  roleId: number,
  payload: AdminRoleUpdate
): Promise<AdminRoleResponse> {
  const response = await api.put<AdminRoleResponse>(
    `/api/admin/roles/${roleId}`,
    payload
  );

  return response.data;
}

export async function createAdminPermission(
  payload: AdminPermissionCreate
): Promise<AdminPermissionResponse> {
  const response =
    await api.post<AdminPermissionResponse>(
      "/api/admin/permissions",
      payload
    );

  return response.data;
}

export async function updateAdminPermission(
  permissionId: number,
  payload: AdminPermissionUpdate
): Promise<AdminPermissionResponse> {
  const response =
    await api.put<AdminPermissionResponse>(
      `/api/admin/permissions/${permissionId}`,
      payload
    );

  return response.data;
}
