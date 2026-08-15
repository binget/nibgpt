import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  FormControlLabel,
  InputLabel,
  LinearProgress,
  MenuItem,
  Paper,
  Select,
  Snackbar,
  Switch,
  TextField,
  Typography,
} from "@mui/material";

import {
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  createBusinessRule,
  deleteBusinessRule,
  getBusinessRules,
  updateBusinessRule,
} from "../../services/businessRules";

import {
  getBusinessDomains,
  getBusinessEntities,
} from "../../services/businessEntities";

import {
  getMetadataTable,
} from "../../services/metadata";

import type {
  BusinessDomain,
  BusinessEntity,
} from "../../types/businessEntity";

import type {
  MetadataColumn,
  MetadataTableDetail,
} from "../../types/metadata";

import type {
  BusinessRule,
  BusinessRuleApprovalStatus,
  BusinessRuleCreate,
  BusinessRuleOperator,
} from "../../types/businessRule";


type EntityTableMapping = {
  id: number;
  metadata_table_id: number;
  mapping_type: string;
  confidence: number;
  is_active: boolean;
};

type EntityWithMappings =
  BusinessEntity & {
    table_mappings?: EntityTableMapping[];
  };


const emptyForm: BusinessRuleCreate = {
  business_entity_id: 0,
  metadata_column_id: 0,
  name: "",
  trigger_phrase: "",
  synonyms: "",
  operator: "=",
  rule_value: "",
  description: "",
  confidence: 100,
  approval_status: "draft",
  is_active: true,
};


function BusinessRuleRegistryPage() {
  const [domains, setDomains] =
    useState<BusinessDomain[]>([]);

  const [entities, setEntities] =
    useState<EntityWithMappings[]>([]);

  const [rules, setRules] =
    useState<BusinessRule[]>([]);

  const [selectedDomainId, setSelectedDomainId] =
    useState<number | "">("");

  const [selectedEntityId, setSelectedEntityId] =
    useState<number | "">("");

  const [approvalFilter, setApprovalFilter] =
    useState("");

  const [selectedRule, setSelectedRule] =
    useState<BusinessRule | null>(null);

  const [loading, setLoading] =
    useState(true);

  const [loadingRules, setLoadingRules] =
    useState(false);

  const [dialogOpen, setDialogOpen] =
    useState(false);

  const [editingRule, setEditingRule] =
    useState<BusinessRule | null>(null);

  const [saving, setSaving] =
    useState(false);

  const [form, setForm] =
    useState<BusinessRuleCreate>(
      emptyForm
    );

  const [availableColumns, setAvailableColumns] =
    useState<
      {
        table: MetadataTableDetail;
        column: MetadataColumn;
      }[]
    >([]);

  const [loadingColumns, setLoadingColumns] =
    useState(false);

  const [message, setMessage] =
    useState("");

  const [messageType, setMessageType] =
    useState<"success" | "error">(
      "success"
    );


  const showMessage = (
    text: string,
    type: "success" | "error"
  ) => {
    setMessage(text);
    setMessageType(type);
  };


  const loadInitialData = async () => {
    try {
      setLoading(true);

      const [
        domainResult,
        entityResult,
        ruleResult,
      ] = await Promise.all([
        getBusinessDomains(),
        getBusinessEntities(),
        getBusinessRules(),
      ]);

      setDomains(domainResult);

      setEntities(
        entityResult as EntityWithMappings[]
      );

      setRules(ruleResult);

      if (domainResult.length > 0) {
        setSelectedDomainId(
          domainResult[0].id
        );
      }
    } catch (error: any) {
      showMessage(
        error?.response?.data?.detail ??
          "Unable to load the Business Rule Registry.",
        "error"
      );
    } finally {
      setLoading(false);
    }
  };


  const loadRules = async () => {
    try {
      setLoadingRules(true);

      const result =
        await getBusinessRules(
          selectedEntityId === ""
            ? undefined
            : selectedEntityId,
          approvalFilter || undefined
        );

      setRules(result);
      setSelectedRule(null);
    } catch (error: any) {
      showMessage(
        error?.response?.data?.detail ??
          "Unable to load business rules.",
        "error"
      );
    } finally {
      setLoadingRules(false);
    }
  };


  useEffect(() => {
    loadInitialData();
  }, []);


  useEffect(() => {
    if (!loading) {
      loadRules();
    }
  }, [
    selectedEntityId,
    approvalFilter,
  ]);


  const activeDomains = useMemo(
    () =>
      domains.filter(
        (domain) => domain.is_active
      ),
    [domains]
  );


  const domainEntities = useMemo(() => {
    if (selectedDomainId === "") {
      return entities;
    }

    return entities.filter(
      (entity) =>
        entity.domain_id ===
        selectedDomainId
    );
  }, [
    entities,
    selectedDomainId,
  ]);


  const approvedRules = useMemo(
    () =>
      rules.filter(
        (rule) =>
          rule.approval_status ===
          "approved"
      ).length,
    [rules]
  );


  const pendingRules = useMemo(
    () =>
      rules.filter(
        (rule) =>
          rule.approval_status ===
            "draft" ||
          rule.approval_status ===
            "generated"
      ).length,
    [rules]
  );


  const averageConfidence = useMemo(() => {
    if (!rules.length) {
      return 0;
    }

    return Math.round(
      rules.reduce(
        (total, rule) =>
          total + rule.confidence,
        0
      ) / rules.length
    );
  }, [rules]);


  const loadEntityColumns = async (
    entityId: number
  ) => {
    try {
      setLoadingColumns(true);
      setAvailableColumns([]);

      const entity = entities.find(
        (item) =>
          item.id === entityId
      );

      if (!entity) {
        return;
      }

      const mappings = (
        entity.table_mappings ?? []
      ).filter(
        (mapping) =>
          mapping.is_active
      );

      if (!mappings.length) {
        return;
      }

      const tableResults =
        await Promise.all(
          mappings.map(
            async (mapping) => {
              const result =
                await getMetadataTable(
                  mapping.metadata_table_id
                );

              return result as
                MetadataTableDetail;
            }
          )
        );

      const result: {
        table: MetadataTableDetail;
        column: MetadataColumn;
      }[] = [];

      for (
        const table
        of tableResults
      ) {
        for (
          const column
          of table.columns ?? []
        ) {
          if (
            !column.is_enabled ||
            !column.ai_access_allowed
          ) {
            continue;
          }

          result.push({
            table,
            column,
          });
        }
      }

      setAvailableColumns(result);
    } catch (error: any) {
      showMessage(
        error?.response?.data?.detail ??
          "Unable to load metadata columns.",
        "error"
      );
    } finally {
      setLoadingColumns(false);
    }
  };


  const openCreateRule = async () => {
    setEditingRule(null);

    const entityId =
      selectedEntityId === ""
        ? 0
        : selectedEntityId;

    setForm({
      ...emptyForm,
      business_entity_id:
        entityId,
    });

    setAvailableColumns([]);

    if (entityId) {
      await loadEntityColumns(
        entityId
      );
    }

    setDialogOpen(true);
  };


  const openEditRule = async (
    rule: BusinessRule
  ) => {
    setEditingRule(rule);

    setForm({
      business_entity_id:
        rule.business_entity_id,
      metadata_column_id:
        rule.metadata_column_id,
      name: rule.name,
      trigger_phrase:
        rule.trigger_phrase,
      synonyms:
        rule.synonyms ?? "",
      operator: rule.operator,
      rule_value:
        rule.rule_value,
      description:
        rule.description ?? "",
      confidence:
        rule.confidence,
      approval_status:
        rule.approval_status,
      is_active:
        rule.is_active,
    });

    await loadEntityColumns(
      rule.business_entity_id
    );

    setDialogOpen(true);
  };


  const saveRule = async () => {
    if (!form.business_entity_id) {
      showMessage(
        "Business entity is required.",
        "error"
      );
      return;
    }

    if (!form.metadata_column_id) {
      showMessage(
        "Metadata column is required.",
        "error"
      );
      return;
    }

    if (!form.name.trim()) {
      showMessage(
        "Rule name is required.",
        "error"
      );
      return;
    }

    if (!form.trigger_phrase.trim()) {
      showMessage(
        "Trigger phrase is required.",
        "error"
      );
      return;
    }

    if (!form.rule_value.trim()) {
      showMessage(
        "Rule value is required.",
        "error"
      );
      return;
    }

    try {
      setSaving(true);

      const payload:
        BusinessRuleCreate = {
        ...form,
        name:
          form.name.trim(),
        trigger_phrase:
          form.trigger_phrase.trim(),
        synonyms:
          form.synonyms?.trim() ||
          null,
        rule_value:
          form.rule_value.trim(),
        description:
          form.description?.trim() ||
          null,
      };

      if (editingRule) {
        const updated =
          await updateBusinessRule(
            editingRule.id,
            payload
          );

        setRules((current) =>
          current.map((rule) =>
            rule.id === updated.id
              ? updated
              : rule
          )
        );

        setSelectedRule(updated);

        showMessage(
          "Business rule updated successfully.",
          "success"
        );
      } else {
        const created =
          await createBusinessRule(
            payload
          );

        setRules((current) => [
          ...current,
          created,
        ]);

        setSelectedRule(created);

        showMessage(
          "Business rule created successfully.",
          "success"
        );
      }

      setDialogOpen(false);

    } catch (error: any) {
      showMessage(
        error?.response?.data?.detail ??
          "Unable to save business rule.",
        "error"
      );
    } finally {
      setSaving(false);
    }
  };


  const updateApproval = async (
    rule: BusinessRule,
    approvalStatus:
      BusinessRuleApprovalStatus
  ) => {
    try {
      const updated =
        await updateBusinessRule(
          rule.id,
          {
            approval_status:
              approvalStatus,
          }
        );

      setRules((current) =>
        current.map((item) =>
          item.id === updated.id
            ? updated
            : item
        )
      );

      if (
        selectedRule?.id ===
        updated.id
      ) {
        setSelectedRule(updated);
      }

      showMessage(
        approvalStatus === "approved"
          ? "Business rule approved."
          : approvalStatus ===
              "rejected"
            ? "Business rule rejected."
            : "Business rule updated.",
        approvalStatus === "rejected"
          ? "error"
          : "success"
      );

    } catch (error: any) {
      showMessage(
        error?.response?.data?.detail ??
          "Unable to update approval status.",
        "error"
      );
    }
  };


  const toggleRuleActive = async (
    rule: BusinessRule
  ) => {
    try {
      const updated =
        await updateBusinessRule(
          rule.id,
          {
            is_active:
              !rule.is_active,
          }
        );

      setRules((current) =>
        current.map((item) =>
          item.id === updated.id
            ? updated
            : item
        )
      );

      setSelectedRule(updated);

      showMessage(
        updated.is_active
          ? "Business rule enabled."
          : "Business rule disabled.",
        "success"
      );

    } catch (error: any) {
      showMessage(
        error?.response?.data?.detail ??
          "Unable to update rule status.",
        "error"
      );
    }
  };


  const removeRule = async (
    ruleId: number
  ) => {
    const confirmed =
      window.confirm(
        "Delete this business rule?"
      );

    if (!confirmed) {
      return;
    }

    try {
      await deleteBusinessRule(
        ruleId
      );

      setRules((current) =>
        current.filter(
          (rule) =>
            rule.id !== ruleId
        )
      );

      setSelectedRule(null);

      showMessage(
        "Business rule deleted.",
        "success"
      );

    } catch (error: any) {
      showMessage(
        error?.response?.data?.detail ??
          "Unable to delete business rule.",
        "error"
      );
    }
  };


  if (loading) {
    return (
      <Box
        sx={{
          minHeight: 500,
          display: "grid",
          placeItems: "center",
        }}
      >
        <Box
          sx={{
            textAlign: "center",
          }}
        >
          <CircularProgress
            sx={{
              color: "#a97826",
            }}
          />

          <Typography
            sx={{
              mt: 2,
              color: "#777777",
            }}
          >
            Loading business rules...
          </Typography>
        </Box>
      </Box>
    );
  }


  return (
    <Box>
      <Box
        sx={{
          mb: 3,
          display: "flex",
          justifyContent:
            "space-between",
          alignItems: {
            xs: "flex-start",
            md: "center",
          },
          flexDirection: {
            xs: "column",
            md: "row",
          },
          gap: 2,
        }}
      >
        <Box>
          <Typography
            variant="h4"
            sx={{
              color: "#4f2c1a",
              fontWeight: 900,
            }}
          >
            Business Rule Registry
          </Typography>

          <Typography
            sx={{
              mt: 0.7,
              color: "#777777",
            }}
          >
            Govern how business language
            translates into trusted data
            conditions for NIBGPT.
          </Typography>
        </Box>

        <Button
          variant="contained"
          onClick={openCreateRule}
          sx={{
            textTransform: "none",
            fontWeight: 800,
            background:
              "linear-gradient(90deg, #61351f, #c78f2b)",
          }}
        >
          New Business Rule
        </Button>
      </Box>


      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: {
            xs: "1fr",
            md: "repeat(3, 1fr)",
          },
          gap: 2,
          mb: 2.5,
        }}
      >
        <SummaryCard
          label="Approved Rules"
          value={String(
            approvedRules
          )}
          description="Trusted business semantics available to NIBGPT"
        />

        <SummaryCard
          label="Pending Review"
          value={String(
            pendingRules
          )}
          description="Draft or generated rules awaiting governance"
        />

        <SummaryCard
          label="Average Confidence"
          value={`${averageConfidence}%`}
          description="Confidence across displayed business rules"
        />
      </Box>


      <Paper
        elevation={0}
        sx={{
          p: 2.5,
          mb: 2.5,
          borderRadius: 3,
          border:
            "1px solid #e9e2da",
        }}
      >
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: {
              xs: "1fr",
              md:
                "repeat(3, minmax(0, 1fr))",
            },
            gap: 2,
          }}
        >
          <FormControl fullWidth>
            <InputLabel>
              Business domain
            </InputLabel>

            <Select
              label="Business domain"
              value={selectedDomainId}
              onChange={(event) => {
                const value =
                  Number(
                    event.target.value
                  );

                setSelectedDomainId(
                  value
                );

                setSelectedEntityId(
                  ""
                );
              }}
            >
              {activeDomains.map(
                (domain) => (
                  <MenuItem
                    key={domain.id}
                    value={domain.id}
                  >
                    {domain.name}
                  </MenuItem>
                )
              )}
            </Select>
          </FormControl>


          <FormControl fullWidth>
            <InputLabel>
              Business entity
            </InputLabel>

            <Select
                label="Business entity"
                value={
                    selectedEntityId === ""
                    ? 0
                    : selectedEntityId
                }
                onChange={(event) => {
                    const value = Number(
                    event.target.value
                    );

                    setSelectedEntityId(
                    value === 0
                        ? ""
                        : value
                    );
                }}
                >
                <MenuItem value={0}>
                    All entities
                </MenuItem>

                {domainEntities.map(
                    (entity) => (
                    <MenuItem
                        key={entity.id}
                        value={entity.id}
                    >
                        {entity.name}
                    </MenuItem>
                    )
                )}
                </Select>
          </FormControl>


          <FormControl fullWidth>
            <InputLabel>
              Approval status
            </InputLabel>

            <Select
              label="Approval status"
              value={approvalFilter}
              onChange={(event) =>
                setApprovalFilter(
                  event.target.value
                )
              }
            >
              <MenuItem value="">
                All statuses
              </MenuItem>

              <MenuItem value="draft">
                Draft
              </MenuItem>

              <MenuItem value="generated">
                Generated
              </MenuItem>

              <MenuItem value="approved">
                Approved
              </MenuItem>

              <MenuItem value="rejected">
                Rejected
              </MenuItem>
            </Select>
          </FormControl>
        </Box>
      </Paper>


      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: {
            xs: "1fr",
            xl: "0.95fr 1.45fr",
          },
          gap: 2.5,
        }}
      >
        <Paper
          elevation={0}
          sx={{
            minHeight: 620,
            borderRadius: 3,
            border:
              "1px solid #e9e2da",
            overflow: "hidden",
          }}
        >
          <Box
            sx={{
              px: 2.5,
              py: 2,
              borderBottom:
                "1px solid #eee7df",
            }}
          >
            <Typography
              variant="h6"
              sx={{
                color: "#4f2c1a",
                fontWeight: 900,
              }}
            >
              Business Rules
            </Typography>

            <Typography
              variant="body2"
              sx={{
                color: "#888888",
              }}
            >
              Select a governed rule
              to inspect its meaning.
            </Typography>
          </Box>

          <Box
            sx={{
              p: 1.5,
              maxHeight: 740,
              overflowY: "auto",
            }}
          >
            {loadingRules ? (
              <Box
                sx={{
                  minHeight: 360,
                  display: "grid",
                  placeItems: "center",
                }}
              >
                <CircularProgress
                  sx={{
                    color: "#a97826",
                  }}
                />
              </Box>
            ) : rules.length === 0 ? (
              <EmptyState
                title="No rules found"
                description="Create business rules that translate business language into governed data conditions."
              />
            ) : (
              rules.map(
                (rule) => (
                  <RuleListItem
                    key={rule.id}
                    rule={rule}
                    selected={
                      selectedRule?.id ===
                      rule.id
                    }
                    onClick={() =>
                      setSelectedRule(
                        rule
                      )
                    }
                  />
                )
              )
            )}
          </Box>
        </Paper>


        <Paper
          elevation={0}
          sx={{
            minHeight: 620,
            borderRadius: 3,
            border:
              "1px solid #e9e2da",
            overflow: "hidden",
          }}
        >
          {!selectedRule ? (
            <EmptyState
              title="Select a business rule"
              description="Choose a rule to inspect its trigger, physical column, operator, value and governance state."
            />
          ) : (
            <RuleDetails
              rule={selectedRule}
              onEdit={() =>
                openEditRule(
                  selectedRule
                )
              }
              onApprove={() =>
                updateApproval(
                  selectedRule,
                  "approved"
                )
              }
              onReject={() =>
                updateApproval(
                  selectedRule,
                  "rejected"
                )
              }
              onToggleActive={() =>
                toggleRuleActive(
                  selectedRule
                )
              }
              onDelete={() =>
                removeRule(
                  selectedRule.id
                )
              }
            />
          )}
        </Paper>
      </Box>


      <RuleDialog
        open={dialogOpen}
        editing={
          Boolean(editingRule)
        }
        entities={entities}
        form={form}
        availableColumns={
          availableColumns
        }
        loadingColumns={
          loadingColumns
        }
        saving={saving}
        onFormChange={setForm}
        onEntityChange={
          async (entityId) => {
            setForm(
              (current) => ({
                ...current,
                business_entity_id:
                  entityId,
                metadata_column_id: 0,
              })
            );

            await loadEntityColumns(
              entityId
            );
          }
        }
        onClose={() =>
          setDialogOpen(false)
        }
        onSave={saveRule}
      />


      <Snackbar
        open={Boolean(message)}
        autoHideDuration={6000}
        onClose={() =>
          setMessage("")
        }
        anchorOrigin={{
          vertical: "bottom",
          horizontal: "right",
        }}
      >
        <Alert
          severity={messageType}
          variant="filled"
          onClose={() =>
            setMessage("")
          }
        >
          {message}
        </Alert>
      </Snackbar>
    </Box>
  );
}


function SummaryCard({
  label,
  value,
  description,
}: {
  label: string;
  value: string;
  description: string;
}) {
  return (
    <Paper
      elevation={0}
      sx={{
        p: 2.5,
        borderRadius: 3,
        border:
          "1px solid #e9e2da",
      }}
    >
      <Typography
        variant="body2"
        sx={{
          color: "#777777",
          fontWeight: 700,
        }}
      >
        {label}
      </Typography>

      <Typography
        variant="h4"
        sx={{
          mt: 1,
          color: "#4f2c1a",
          fontWeight: 900,
        }}
      >
        {value}
      </Typography>

      <Typography
        variant="caption"
        sx={{
          color: "#999999",
        }}
      >
        {description}
      </Typography>
    </Paper>
  );
}


function RuleListItem({
  rule,
  selected,
  onClick,
}: {
  rule: BusinessRule;
  selected: boolean;
  onClick: () => void;
}) {
  return (
    <Box
      onClick={onClick}
      sx={{
        p: 1.8,
        mb: 1,
        cursor: "pointer",
        borderRadius: 2.5,
        border: selected
          ? "1px solid #d2a244"
          : "1px solid transparent",
        bgcolor: selected
          ? "#fff3dc"
          : "#faf8f5",
        transition:
          "all 0.18s ease",
        "&:hover": {
          transform:
            "translateX(3px)",
          borderColor:
            "#d9bd8a",
        },
      }}
    >
      <Box
        sx={{
          display: "flex",
          justifyContent:
            "space-between",
          gap: 1,
        }}
      >
        <Box>
          <Typography
            sx={{
              color: "#4f2c1a",
              fontWeight: 900,
            }}
          >
            {rule.name}
          </Typography>

          <Typography
            variant="body2"
            sx={{
              mt: 0.5,
              color: "#777777",
            }}
          >
            {rule.entity.name}
          </Typography>

          <Typography
            variant="body2"
            sx={{
              mt: 0.5,
              color: "#a06b1f",
              fontWeight: 800,
            }}
          >
            {rule.column.business_name ??
              rule.column.column_name}
            {" "}
            {rule.operator}
            {" "}
            {rule.rule_value}
          </Typography>
        </Box>

        <RuleStatusChip
          status={
            rule.approval_status
          }
        />
      </Box>

      <LinearProgress
        variant="determinate"
        value={rule.confidence}
        sx={{
          mt: 1.5,
          height: 6,
          borderRadius: 5,
        }}
      />

      <Typography
        variant="caption"
        sx={{
          display: "block",
          mt: 0.5,
          color: "#777777",
        }}
      >
        Trigger:{" "}
        {rule.trigger_phrase}
        {" · "}
        {rule.confidence}%
      </Typography>
    </Box>
  );
}


function RuleDetails({
  rule,
  onEdit,
  onApprove,
  onReject,
  onToggleActive,
  onDelete,
}: {
  rule: BusinessRule;
  onEdit: () => void;
  onApprove: () => void;
  onReject: () => void;
  onToggleActive: () => void;
  onDelete: () => void;
}) {
  return (
    <>
      <Box
        sx={{
          p: 3,
          color: "#ffffff",
          background:
            "linear-gradient(135deg, #5b311b, #9a672c)",
        }}
      >
        <Box
          sx={{
            display: "flex",
            justifyContent:
              "space-between",
            alignItems:
              "flex-start",
            flexWrap: "wrap",
            gap: 2,
          }}
        >
          <Box>
            <Typography
              variant="h5"
              sx={{
                fontWeight: 900,
              }}
            >
              {rule.name}
            </Typography>

            <Typography
              sx={{
                mt: 1,
                color: "#ffdca0",
                fontWeight: 800,
              }}
            >
              Trigger:{" "}
              {rule.trigger_phrase}
            </Typography>
          </Box>

          <Box
            sx={{
              display: "flex",
              gap: 1,
            }}
          >
            <RuleStatusChip
              status={
                rule.approval_status
              }
            />

            <Button
              variant="contained"
              onClick={onEdit}
              sx={{
                bgcolor: "#ffffff",
                color: "#5b311b",
                textTransform:
                  "none",
                fontWeight: 800,
              }}
            >
              Edit Rule
            </Button>
          </Box>
        </Box>

        <Typography
          sx={{
            mt: 2,
            color:
              "rgba(255,255,255,0.78)",
          }}
        >
          {rule.description ||
            "No business rule description has been added."}
        </Typography>
      </Box>


      <Box sx={{ p: 3 }}>
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: {
              xs: "1fr",
              md:
                "repeat(2, 1fr)",
            },
            gap: 2,
          }}
        >
          <InfoPanel
            title="Business Meaning"
          >
            <DetailLine
              label="Entity"
              value={
                rule.entity.name
              }
            />

            <DetailLine
              label="Trigger"
              value={
                rule.trigger_phrase
              }
            />

            <DetailLine
              label="Synonyms"
              value={
                rule.synonyms ||
                "None"
              }
            />
          </InfoPanel>


          <InfoPanel
            title="Physical Rule"
          >
            <DetailLine
              label="Column"
              value={
                rule.column
                  .business_name ??
                rule.column
                  .column_name
              }
            />

            <DetailLine
              label="Technical"
              value={
                rule.column
                  .column_name
              }
            />

            <DetailLine
              label="Condition"
              value={
                `${rule.operator} ${rule.rule_value}`
              }
            />
          </InfoPanel>


          <InfoPanel
            title="Confidence"
          >
            <Typography
              variant="h3"
              sx={{
                color: "#4f2c1a",
                fontWeight: 900,
              }}
            >
              {rule.confidence}%
            </Typography>

            <LinearProgress
              variant="determinate"
              value={
                rule.confidence
              }
              sx={{
                mt: 1.5,
                height: 9,
                borderRadius: 5,
              }}
            />
          </InfoPanel>


          <InfoPanel
            title="Governance"
          >
            <RuleStatusChip
              status={
                rule.approval_status
              }
            />

            <Typography
              variant="body2"
              sx={{
                mt: 1.5,
                color: "#777777",
              }}
            >
              {rule.is_active
                ? "Active and available to the governed planner."
                : "Disabled and ignored by the governed planner."}
            </Typography>

            {rule.column.is_sensitive && (
              <Chip
                label="Sensitive Column"
                color="warning"
                size="small"
                sx={{
                  mt: 1.5,
                }}
              />
            )}
          </InfoPanel>
        </Box>


        <Box
          sx={{
            mt: 3,
            pt: 2.5,
            borderTop:
              "1px solid #eee7df",
            display: "flex",
            justifyContent:
              "space-between",
            flexWrap: "wrap",
            gap: 1,
          }}
        >
          <Box
            sx={{
              display: "flex",
              gap: 1,
              flexWrap: "wrap",
            }}
          >
            <Button
              variant="outlined"
              onClick={
                onToggleActive
              }
              sx={{
                textTransform:
                  "none",
                fontWeight: 800,
                color: "#6b3b21",
                borderColor:
                  "#9f795d",
              }}
            >
              {rule.is_active
                ? "Disable"
                : "Enable"}
            </Button>

            <Button
              variant="outlined"
              color="error"
              onClick={onDelete}
              sx={{
                textTransform:
                  "none",
                fontWeight: 800,
              }}
            >
              Delete
            </Button>
          </Box>

          <Box
            sx={{
              display: "flex",
              gap: 1,
              flexWrap: "wrap",
            }}
          >
            <Button
              variant="outlined"
              color="error"
              onClick={onReject}
              sx={{
                textTransform:
                  "none",
                fontWeight: 800,
              }}
            >
              Reject
            </Button>

            <Button
              variant="contained"
              onClick={onApprove}
              sx={{
                bgcolor: "#28774b",
                textTransform:
                  "none",
                fontWeight: 800,
              }}
            >
              Approve Rule
            </Button>
          </Box>
        </Box>
      </Box>
    </>
  );
}


function RuleDialog({
  open,
  editing,
  entities,
  form,
  availableColumns,
  loadingColumns,
  saving,
  onFormChange,
  onEntityChange,
  onClose,
  onSave,
}: {
  open: boolean;
  editing: boolean;
  entities: EntityWithMappings[];
  form: BusinessRuleCreate;
  availableColumns: {
    table: MetadataTableDetail;
    column: MetadataColumn;
  }[];
  loadingColumns: boolean;
  saving: boolean;
  onFormChange:
    React.Dispatch<
      React.SetStateAction<BusinessRuleCreate>
    >;
  onEntityChange:
    (entityId: number) => void;
  onClose: () => void;
  onSave: () => void;
}) {
  return (
    <Dialog
      open={open}
      onClose={() => {
        if (!saving) {
          onClose();
        }
      }}
      fullWidth
      maxWidth="md"
    >
      <DialogTitle
        sx={{
          color: "#4f2c1a",
          fontWeight: 900,
        }}
      >
        {editing
          ? "Edit Business Rule"
          : "Create Business Rule"}
      </DialogTitle>

      <DialogContent dividers>
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: {
              xs: "1fr",
              md:
                "repeat(2, 1fr)",
            },
            gap: 2,
          }}
        >
          <FormControl
            fullWidth
            disabled={editing}
          >
            <InputLabel>
              Business entity
            </InputLabel>

            <Select
              label="Business entity"
              value={
                form.business_entity_id ||
                ""
              }
              onChange={(event) =>
                onEntityChange(
                  Number(
                    event.target.value
                  )
                )
              }
            >
              {entities.map(
                (entity) => (
                  <MenuItem
                    key={entity.id}
                    value={entity.id}
                  >
                    {entity.name}
                  </MenuItem>
                )
              )}
            </Select>
          </FormControl>


          <FormControl
            fullWidth
            disabled={
              !form.business_entity_id ||
              loadingColumns
            }
          >
            <InputLabel>
              Metadata column
            </InputLabel>

            <Select
              label="Metadata column"
              value={
                form.metadata_column_id ||
                ""
              }
              onChange={(event) =>
                onFormChange(
                  (current) => ({
                    ...current,
                    metadata_column_id:
                      Number(
                        event.target.value
                      ),
                  })
                )
              }
            >
              {availableColumns.map(
                ({
                  table,
                  column,
                }) => (
                  <MenuItem
                    key={column.id}
                    value={column.id}
                  >
                    {table.business_name ??
                      table.table_name}
                    {" → "}
                    {column.business_name ??
                      column.column_name}
                  </MenuItem>
                )
              )}
            </Select>
          </FormControl>


          <TextField
            label="Rule name"
            value={form.name}
            onChange={(event) =>
              onFormChange(
                (current) => ({
                  ...current,
                  name:
                    event.target.value,
                })
              )
            }
            placeholder="Emergency Trip"
          />


          <TextField
            label="Trigger phrase"
            value={
              form.trigger_phrase
            }
            onChange={(event) =>
              onFormChange(
                (current) => ({
                  ...current,
                  trigger_phrase:
                    event.target.value,
                })
              )
            }
            placeholder="emergency"
          />


          <TextField
            label="Synonyms"
            value={
              form.synonyms ?? ""
            }
            onChange={(event) =>
              onFormChange(
                (current) => ({
                  ...current,
                  synonyms:
                    event.target.value,
                })
              )
            }
            placeholder='["urgent trip", "emergency trip"]'
          />


          <FormControl fullWidth>
            <InputLabel>
              Operator
            </InputLabel>

            <Select
              label="Operator"
              value={form.operator}
              onChange={(event) =>
                onFormChange(
                  (current) => ({
                    ...current,
                    operator:
                      event.target
                        .value as
                        BusinessRuleOperator,
                  })
                )
              }
            >
              {[
  "=",
  "!=",
  ">",
  ">=",
  "<",
  "<=",
  "like",
  "not like",
  "between_or_between",
].map(
  (operator) => (
    <MenuItem
      key={operator}
      value={operator}
    >
      {operator === "between_or_between"
        ? "Between Two Ranges"
        : operator}
    </MenuItem>
  )
)}
            </Select>
          </FormControl>


          <TextField
            label="Rule value"
            value={
              form.rule_value
            }
            onChange={(event) =>
              onFormChange(
                (current) => ({
                  ...current,
                  rule_value:
                    event.target.value,
                })
              )
            }
            placeholder="Yes"
          />


          <TextField
            label="Confidence"
            type="number"
            value={
              form.confidence
            }
            onChange={(event) =>
              onFormChange(
                (current) => ({
                  ...current,
                  confidence:
                    Math.max(
                      0,
                      Math.min(
                        100,
                        Number(
                          event.target
                            .value
                        )
                      )
                    ),
                })
              )
            }
          />


          <FormControl fullWidth>
            <InputLabel>
              Approval status
            </InputLabel>

            <Select
              label="Approval status"
              value={
                form.approval_status
              }
              onChange={(event) =>
                onFormChange(
                  (current) => ({
                    ...current,
                    approval_status:
                      event.target
                        .value as
                        BusinessRuleApprovalStatus,
                  })
                )
              }
            >
              <MenuItem value="draft">
                Draft
              </MenuItem>

              <MenuItem value="generated">
                Generated
              </MenuItem>

              <MenuItem value="approved">
                Approved
              </MenuItem>

              <MenuItem value="rejected">
                Rejected
              </MenuItem>
            </Select>
          </FormControl>


          <TextField
            multiline
            minRows={4}
            label="Description"
            value={
              form.description ?? ""
            }
            onChange={(event) =>
              onFormChange(
                (current) => ({
                  ...current,
                  description:
                    event.target.value,
                })
              )
            }
            sx={{
              gridColumn: {
                xs: "auto",
                md: "1 / -1",
              },
            }}
          />


          <FormControlLabel
            control={
              <Switch
                checked={
                  form.is_active
                }
                onChange={(
                  event
                ) =>
                  onFormChange(
                    (current) => ({
                      ...current,
                      is_active:
                        event.target
                          .checked,
                    })
                  )
                }
              />
            }
            label="Rule is active"
          />
        </Box>
      </DialogContent>

      <DialogActions
        sx={{
          px: 3,
          py: 2,
        }}
      >
        <Button
          disabled={saving}
          onClick={onClose}
          sx={{
            textTransform: "none",
          }}
        >
          Cancel
        </Button>

        <Button
          variant="contained"
          disabled={saving}
          onClick={onSave}
          sx={{
            textTransform: "none",
            fontWeight: 800,
            background:
              "linear-gradient(90deg, #61351f, #c78f2b)",
          }}
        >
          {saving
            ? "Saving..."
            : "Save Rule"}
        </Button>
      </DialogActions>
    </Dialog>
  );
}


function InfoPanel({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <Paper
      elevation={0}
      sx={{
        p: 2.5,
        borderRadius: 3,
        bgcolor: "#faf8f5",
        border:
          "1px solid #ece5dd",
      }}
    >
      <Typography
        sx={{
          mb: 1.5,
          color: "#4f2c1a",
          fontWeight: 900,
        }}
      >
        {title}
      </Typography>

      {children}
    </Paper>
  );
}


function DetailLine({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <Box
      sx={{
        display: "flex",
        justifyContent:
          "space-between",
        gap: 2,
        mb: 1,
      }}
    >
      <Typography
        variant="body2"
        sx={{
          color: "#888888",
        }}
      >
        {label}
      </Typography>

      <Typography
        variant="body2"
        sx={{
          color: "#4f2c1a",
          fontWeight: 800,
        }}
      >
        {value}
      </Typography>
    </Box>
  );
}


function EmptyState({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <Box
      sx={{
        minHeight: 430,
        display: "grid",
        placeItems: "center",
        p: 4,
        textAlign: "center",
      }}
    >
      <Box>
        <Box
          sx={{
            width: 82,
            height: 82,
            mx: "auto",
            mb: 2,
            borderRadius: 4,
            display: "grid",
            placeItems: "center",
            bgcolor: "#fff3dc",
            color: "#8b5d12",
            fontWeight: 900,
          }}
        >
          BR
        </Box>

        <Typography
          variant="h6"
          sx={{
            color: "#4f2c1a",
            fontWeight: 900,
          }}
        >
          {title}
        </Typography>

        <Typography
          variant="body2"
          sx={{
            mt: 1,
            color: "#888888",
            maxWidth: 440,
          }}
        >
          {description}
        </Typography>
      </Box>
    </Box>
  );
}


function RuleStatusChip({
  status,
}: {
  status: string;
}) {
  const settings:
    Record<
      string,
      {
        label: string;
        background: string;
        color: string;
      }
    > = {
    draft: {
      label: "Draft",
      background: "#eeeeee",
      color: "#666666",
    },
    generated: {
      label: "Generated",
      background: "#fff3dc",
      color: "#8b5d12",
    },
    approved: {
      label: "Approved",
      background: "#e7f6ed",
      color: "#207744",
    },
    rejected: {
      label: "Rejected",
      background: "#fdecec",
      color: "#b3261e",
    },
  };

  const selected =
    settings[status] ??
    settings.draft;

  return (
    <Chip
      label={selected.label}
      size="small"
      sx={{
        bgcolor:
          selected.background,
        color:
          selected.color,
        fontWeight: 800,
      }}
    />
  );
}


export default BusinessRuleRegistryPage;