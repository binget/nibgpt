import api from "./api";

import type {
  BusinessRule,
  BusinessRuleCreate,
  BusinessRuleUpdate,
} from "../types/businessRule";


export async function getBusinessRules(
  businessEntityId?: number,
  approvalStatus?: string,
  isActive?: boolean
): Promise<BusinessRule[]> {
  const response = await api.get<BusinessRule[]>(
    "/api/business-rules",
    {
      params: {
        business_entity_id: businessEntityId,
        approval_status:
          approvalStatus || undefined,
        is_active:
          isActive === undefined
            ? undefined
            : isActive,
      },
    }
  );

  return response.data;
}


export async function getBusinessRule(
  ruleId: number
): Promise<BusinessRule> {
  const response = await api.get<BusinessRule>(
    `/api/business-rules/${ruleId}`
  );

  return response.data;
}


export async function createBusinessRule(
  payload: BusinessRuleCreate
): Promise<BusinessRule> {
  const response = await api.post<BusinessRule>(
    "/api/business-rules",
    payload
  );

  return response.data;
}


export async function updateBusinessRule(
  ruleId: number,
  payload: BusinessRuleUpdate
): Promise<BusinessRule> {
  const response = await api.put<BusinessRule>(
    `/api/business-rules/${ruleId}`,
    payload
  );

  return response.data;
}


export async function deleteBusinessRule(
  ruleId: number
): Promise<void> {
  await api.delete(
    `/api/business-rules/${ruleId}`
  );
}