export interface DomainReadiness {
  data_source_id: number;
  domain_name: string;
  database_type: string;

  readiness_score: number;
  maturity_level: string;
  status: string;

  approved_knowledge_percentage: number;
  approved_dictionary_percentage: number;
  governance_percentage: number;

  requires_attention: boolean;
  attention_reason: string | null;
}

export interface ExecutiveHighlight {
  severity:
    | "success"
    | "warning"
    | "info"
    | "error";

  title: string;
  message: string;
}

export interface ExecutiveDashboard {
  enterprise_readiness: number;
  readiness_label: string;

  connected_business_systems: number;
  ai_ready_business_systems: number;
  systems_requiring_attention: number;

  governance_compliance: number;
  knowledge_maturity: number;

  domains: DomainReadiness[];
  highlights: ExecutiveHighlight[];
}
