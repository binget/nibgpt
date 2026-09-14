import api from "./api";

import type {
  AdminRoleListResponse,
  AdminUserCreate,
  AdminUserListResponse,
  AdminUserResponse,
  AdminUserUpdate,
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
