export type DatabaseType = "postgresql" | "mysql" | "oracle";

export interface DataSource {
  id: number;
  name: string;
  code: string;
  database_type: DatabaseType;
  host: string;
  port: number;
  database_name: string | null;
  service_name: string | null;
  username: string;
  description: string | null;
  status: "connected" | "failed" | "not_tested";
  is_active: boolean;
  last_test_message: string | null;
  last_tested_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface DataSourceCreate {
  name: string;
  code: string;
  database_type: DatabaseType;
  host: string;
  port: number;
  database_name: string | null;
  service_name: string | null;
  username: string;
  password: string;
  description: string | null;
  is_active: boolean;
}

export interface ConnectionTestResponse {
  success: boolean;
  status: string;
  message: string;
}
