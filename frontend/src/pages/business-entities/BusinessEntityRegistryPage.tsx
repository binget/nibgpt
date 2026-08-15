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
  createBusinessDomain,
  createBusinessEntity,
  createEntityTableMapping,
  deleteEntityTableMapping,
  getBusinessDomains,
  getBusinessEntities,
  suggestEntityFromTable,
  updateBusinessDomain,
  updateBusinessEntity,
} from "../../services/businessEntities";

import {
  getMetadataTables,
} from "../../services/metadata";

import type {
  BusinessDomain,
  BusinessDomainCreate,
  BusinessEntity,
  BusinessEntityCreate,
  BusinessEntitySuggestion,
  EntityApprovalStatus,
  EntityClassification,
  EntityMappingType,
} from "../../types/businessEntity";

import type {
  MetadataTableSummary,
} from "../../types/metadata";


function BusinessEntityRegistryPage() {
  const [domains, setDomains] =
    useState<BusinessDomain[]>([]);

  const [entities, setEntities] =
    useState<BusinessEntity[]>([]);

  const [metadataTables, setMetadataTables] =
    useState<MetadataTableSummary[]>([]);

  const [selectedDomainId, setSelectedDomainId] =
    useState<number | "">("");

  const [selectedEntity, setSelectedEntity] =
    useState<BusinessEntity | null>(null);

  const [loading, setLoading] =
    useState(true);

  const [loadingEntities, setLoadingEntities] =
    useState(false);

  const [domainDialogOpen, setDomainDialogOpen] =
    useState(false);

  const [entityDialogOpen, setEntityDialogOpen] =
    useState(false);

  const [mappingDialogOpen, setMappingDialogOpen] =
    useState(false);

  const [suggestionDialogOpen, setSuggestionDialogOpen] =
    useState(false);

  const [savingDomain, setSavingDomain] =
    useState(false);

  const [savingEntity, setSavingEntity] =
    useState(false);

  const [savingMapping, setSavingMapping] =
    useState(false);

  const [generatingSuggestion, setGeneratingSuggestion] =
    useState(false);

  const [editingDomain, setEditingDomain] =
    useState<BusinessDomain | null>(null);

  const [editingEntity, setEditingEntity] =
    useState<BusinessEntity | null>(null);

  const [suggestion, setSuggestion] =
    useState<BusinessEntitySuggestion | null>(null);

  const [suggestionTableId, setSuggestionTableId] =
    useState<number | "">("");

  const [message, setMessage] =
    useState("");

  const [messageType, setMessageType] =
    useState<"success" | "error">("success");

  const [domainForm, setDomainForm] =
    useState<BusinessDomainCreate>({
      name: "",
      description: "",
      department: "",
      owner: "",
    });

  const [entityForm, setEntityForm] =
    useState<BusinessEntityCreate>({
      domain_id: 0,
      name: "",
      description: "",
      synonyms: [],
      business_owner: "",
      classification: "internal",
      ai_access_allowed: true,
      confidence: 0,
    });

  const [synonymText, setSynonymText] =
    useState("");

  const [mappingTableId, setMappingTableId] =
    useState<number | "">("");

  const [mappingType, setMappingType] =
    useState<EntityMappingType>("primary");

  const [mappingConfidence, setMappingConfidence] =
    useState(100);


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
        tableResult,
      ] = await Promise.all([
        getBusinessDomains(),
        getBusinessEntities(),
        getMetadataTables(),
      ]);

      setDomains(domainResult);
      setEntities(entityResult);
      setMetadataTables(tableResult);

      if (
        domainResult.length > 0 &&
        selectedDomainId === ""
      ) {
        setSelectedDomainId(
          domainResult[0].id
        );
      }
    } catch (error: any) {
      showMessage(
        error?.response?.data?.detail ??
          "Unable to load the Business Entity Registry.",
        "error"
      );
    } finally {
      setLoading(false);
    }
  };


  const loadEntities = async (
    domainId?: number
  ) => {
    try {
      setLoadingEntities(true);

      const result =
        await getBusinessEntities(domainId);

      setEntities(result);
      setSelectedEntity(null);
    } catch (error: any) {
      showMessage(
        error?.response?.data?.detail ??
          "Unable to load business entities.",
        "error"
      );
    } finally {
      setLoadingEntities(false);
    }
  };


  useEffect(() => {
    loadInitialData();
  }, []);


  useEffect(() => {
    if (selectedDomainId === "") {
      return;
    }

    loadEntities(selectedDomainId);
  }, [selectedDomainId]);


  const selectedDomain =
    domains.find(
      (domain) =>
        domain.id === selectedDomainId
    ) ?? null;


  const activeDomains = useMemo(
    () =>
      domains.filter(
        (domain) => domain.is_active
      ),
    [domains]
  );


  const approvedEntityCount = useMemo(
    () =>
      entities.filter(
        (entity) =>
          entity.approval_status ===
          "approved"
      ).length,
    [entities]
  );


  const mappedEntityCount = useMemo(
    () =>
      entities.filter(
        (entity) =>
          entity.table_mappings.length > 0
      ).length,
    [entities]
  );


  const openCreateDomain = () => {
    setEditingDomain(null);

    setDomainForm({
      name: "",
      description: "",
      department: "",
      owner: "",
    });

    setDomainDialogOpen(true);
  };


  const openEditDomain = (
    domain: BusinessDomain
  ) => {
    setEditingDomain(domain);

    setDomainForm({
      name: domain.name,
      description:
        domain.description ?? "",
      department:
        domain.department ?? "",
      owner:
        domain.owner ?? "",
    });

    setDomainDialogOpen(true);
  };


  const saveDomain = async () => {
    if (!domainForm.name.trim()) {
      showMessage(
        "Domain name is required.",
        "error"
      );
      return;
    }

    try {
      setSavingDomain(true);

      if (editingDomain) {
        const updated =
          await updateBusinessDomain(
            editingDomain.id,
            {
              name: domainForm.name.trim(),
              description:
                domainForm.description?.trim() ||
                null,
              department:
                domainForm.department?.trim() ||
                null,
              owner:
                domainForm.owner?.trim() ||
                null,
            }
          );

        setDomains((current) =>
          current.map((domain) =>
            domain.id === updated.id
              ? updated
              : domain
          )
        );

        showMessage(
          "Business domain updated successfully.",
          "success"
        );
      } else {
        const created =
          await createBusinessDomain({
            name: domainForm.name.trim(),
            description:
              domainForm.description?.trim() ||
              null,
            department:
              domainForm.department?.trim() ||
              null,
            owner:
              domainForm.owner?.trim() ||
              null,
          });

        setDomains((current) =>
          [...current, created].sort(
            (a, b) =>
              a.name.localeCompare(b.name)
          )
        );

        setSelectedDomainId(created.id);

        showMessage(
          "Business domain created successfully.",
          "success"
        );
      }

      setDomainDialogOpen(false);
    } catch (error: any) {
      showMessage(
        error?.response?.data?.detail ??
          "Unable to save business domain.",
        "error"
      );
    } finally {
      setSavingDomain(false);
    }
  };


  const openCreateEntity = () => {
    if (selectedDomainId === "") {
      showMessage(
        "Select a business domain first.",
        "error"
      );
      return;
    }

    setEditingEntity(null);

    setEntityForm({
      domain_id: selectedDomainId,
      name: "",
      description: "",
      synonyms: [],
      business_owner:
        selectedDomain?.owner ?? "",
      classification: "internal",
      ai_access_allowed: true,
      confidence: 0,
    });

    setSynonymText("");
    setEntityDialogOpen(true);
  };


  const openEditEntity = (
    entity: BusinessEntity
  ) => {
    setEditingEntity(entity);

    const parsedSynonyms =
      parseStoredList(entity.synonyms);

    setEntityForm({
      domain_id: entity.domain_id,
      name: entity.name,
      description:
        entity.description ?? "",
      synonyms: parsedSynonyms,
      business_owner:
        entity.business_owner ?? "",
      classification:
        entity.classification,
      ai_access_allowed:
        entity.ai_access_allowed,
      confidence:
        entity.confidence,
    });

    setSynonymText(
      parsedSynonyms.join(", ")
    );

    setEntityDialogOpen(true);
  };


  const saveEntity = async () => {
    if (
      !entityForm.name.trim() ||
      !entityForm.domain_id
    ) {
      showMessage(
        "Domain and entity name are required.",
        "error"
      );
      return;
    }

    const synonyms = synonymText
      .split(/[,;\n]+/)
      .map((value) => value.trim())
      .filter(Boolean);

    try {
      setSavingEntity(true);

      if (editingEntity) {
        const updated =
          await updateBusinessEntity(
            editingEntity.id,
            {
              domain_id:
                entityForm.domain_id,
              name:
                entityForm.name.trim(),
              description:
                entityForm.description?.trim() ||
                null,
              synonyms,
              business_owner:
                entityForm.business_owner?.trim() ||
                null,
              classification:
                entityForm.classification,
              ai_access_allowed:
                entityForm.ai_access_allowed,
              confidence:
                entityForm.confidence,
            }
          );

        setEntities((current) =>
          current.map((entity) =>
            entity.id === updated.id
              ? updated
              : entity
          )
        );

        setSelectedEntity(updated);

        showMessage(
          "Business entity updated successfully.",
          "success"
        );
      } else {
        const created =
          await createBusinessEntity({
            ...entityForm,
            name:
              entityForm.name.trim(),
            description:
              entityForm.description?.trim() ||
              null,
            business_owner:
              entityForm.business_owner?.trim() ||
              null,
            synonyms,
          });

        setEntities((current) =>
          [...current, created].sort(
            (a, b) =>
              a.name.localeCompare(b.name)
          )
        );

        setSelectedEntity(created);

        showMessage(
          "Business entity created successfully.",
          "success"
        );
      }

      setEntityDialogOpen(false);
    } catch (error: any) {
      showMessage(
        error?.response?.data?.detail ??
          "Unable to save business entity.",
        "error"
      );
    } finally {
      setSavingEntity(false);
    }
  };


  const updateEntityApproval = async (
    entity: BusinessEntity,
    status: EntityApprovalStatus
  ) => {
    try {
      const updated =
        await updateBusinessEntity(
          entity.id,
          {
            approval_status: status,
          }
        );

      setEntities((current) =>
        current.map((item) =>
          item.id === updated.id
            ? updated
            : item
        )
      );

      if (
        selectedEntity?.id ===
        updated.id
      ) {
        setSelectedEntity(updated);
      }

      showMessage(
        status === "approved"
          ? "Business entity approved."
          : "Business entity status updated.",
        status === "rejected"
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


  const openMappingDialog = () => {
    if (!selectedEntity) {
      return;
    }

    setMappingTableId("");
    setMappingType("primary");
    setMappingConfidence(100);
    setMappingDialogOpen(true);
  };


  const saveMapping = async () => {
    if (
      !selectedEntity ||
      mappingTableId === ""
    ) {
      showMessage(
        "Select a physical metadata table.",
        "error"
      );
      return;
    }

    try {
      setSavingMapping(true);

      const created =
        await createEntityTableMapping(
          selectedEntity.id,
          {
            metadata_table_id:
              mappingTableId,
            mapping_type:
              mappingType,
            confidence:
              mappingConfidence,
          }
        );

      const updatedEntity = {
        ...selectedEntity,
        table_mappings: [
          ...selectedEntity.table_mappings,
          created,
        ],
      };

      setSelectedEntity(updatedEntity);

      setEntities((current) =>
        current.map((entity) =>
          entity.id ===
          updatedEntity.id
            ? updatedEntity
            : entity
        )
      );

      setMappingDialogOpen(false);

      showMessage(
        "Physical table mapped successfully.",
        "success"
      );
    } catch (error: any) {
      showMessage(
        error?.response?.data?.detail ??
          "Unable to create table mapping.",
        "error"
      );
    } finally {
      setSavingMapping(false);
    }
  };


  const removeMapping = async (
    mappingId: number
  ) => {
    if (!selectedEntity) {
      return;
    }

    try {
      await deleteEntityTableMapping(
        mappingId
      );

      const updatedEntity = {
        ...selectedEntity,
        table_mappings:
          selectedEntity.table_mappings.filter(
            (mapping) =>
              mapping.id !== mappingId
          ),
      };

      setSelectedEntity(updatedEntity);

      setEntities((current) =>
        current.map((entity) =>
          entity.id ===
          updatedEntity.id
            ? updatedEntity
            : entity
        )
      );

      showMessage(
        "Table mapping removed.",
        "success"
      );
    } catch (error: any) {
      showMessage(
        error?.response?.data?.detail ??
          "Unable to remove table mapping.",
        "error"
      );
    }
  };


  const openSuggestionDialog = () => {
    setSuggestion(null);
    setSuggestionTableId("");
    setSuggestionDialogOpen(true);
  };


  const generateSuggestion = async () => {
    if (suggestionTableId === "") {
      showMessage(
        "Select a metadata table first.",
        "error"
      );
      return;
    }

    try {
      setGeneratingSuggestion(true);

      const result =
        await suggestEntityFromTable(
          suggestionTableId
        );

      setSuggestion(result);
    } catch (error: any) {
      showMessage(
        error?.response?.data?.detail ??
          "Unable to generate entity suggestion.",
        "error"
      );
    } finally {
      setGeneratingSuggestion(false);
    }
  };


  const useSuggestion = () => {
    if (!suggestion) {
      return;
    }

    const matchingDomain =
      domains.find(
        (domain) =>
          domain.name.toLowerCase() ===
          suggestion.suggested_domain_name
            .toLowerCase()
      );

    const domainId =
      matchingDomain?.id ??
      (
        selectedDomainId === ""
          ? 0
          : selectedDomainId
      );

    setEditingEntity(null);

    setEntityForm({
      domain_id: domainId,
      name:
        suggestion.suggested_entity_name,
      description:
        suggestion.description,
      synonyms:
        suggestion.synonyms,
      business_owner:
        matchingDomain?.owner ?? "",
      classification: "internal",
      ai_access_allowed: true,
      confidence:
        suggestion.confidence,
    });

    setSynonymText(
      suggestion.synonyms.join(", ")
    );

    setSuggestionDialogOpen(false);
    setEntityDialogOpen(true);
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
        <Box sx={{ textAlign: "center" }}>
          <CircularProgress
            sx={{ color: "#a97826" }}
          />

          <Typography
            sx={{
              mt: 2,
              color: "#777777",
            }}
          >
            Loading enterprise business entities...
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
            Business Entity Registry
          </Typography>

          <Typography
            sx={{
              mt: 0.7,
              color: "#777777",
            }}
          >
            Manage business concepts independently
            from physical database tables.
          </Typography>
        </Box>

        <Box
          sx={{
            display: "flex",
            flexWrap: "wrap",
            gap: 1,
          }}
        >
          <Button
            variant="outlined"
            onClick={openSuggestionDialog}
            sx={{
              textTransform: "none",
              fontWeight: 800,
              color: "#6b3b21",
              borderColor: "#9f795d",
            }}
          >
            Generate Entity Suggestion
          </Button>

          <Button
            variant="outlined"
            onClick={openCreateDomain}
            sx={{
              textTransform: "none",
              fontWeight: 800,
              color: "#6b3b21",
              borderColor: "#9f795d",
            }}
          >
            New Domain
          </Button>

          <Button
            variant="contained"
            onClick={openCreateEntity}
            sx={{
              textTransform: "none",
              fontWeight: 800,
              background:
                "linear-gradient(90deg, #61351f, #c78f2b)",
            }}
          >
            New Business Entity
          </Button>
        </Box>
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
          label="Business Domain"
          value={
            selectedDomain?.name ??
            "Not selected"
          }
          description={
            selectedDomain?.department ??
            "Select a domain"
          }
        />

        <SummaryCard
          label="Approved Entities"
          value={String(
            approvedEntityCount
          )}
          description="Semantic concepts approved for AI use"
        />

        <SummaryCard
          label="Mapped Entities"
          value={String(
            mappedEntityCount
          )}
          description="Entities connected to physical data"
        />
      </Box>

      <Paper
        elevation={0}
        sx={{
          p: 2.5,
          mb: 2.5,
          borderRadius: 3,
          border: "1px solid #e9e2da",
        }}
      >
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: {
              xs: "1fr",
              md: "minmax(260px, 1fr) auto",
            },
            gap: 2,
            alignItems: "center",
          }}
        >
          <FormControl fullWidth>
            <InputLabel>
              Business domain
            </InputLabel>

            <Select
              label="Business domain"
              value={selectedDomainId}
              onChange={(event) =>
                setSelectedDomainId(
                  Number(
                    event.target.value
                  )
                )
              }
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

          {selectedDomain && (
            <Button
              variant="outlined"
              onClick={() =>
                openEditDomain(
                  selectedDomain
                )
              }
              sx={{
                height: 56,
                px: 3,
                textTransform: "none",
                fontWeight: 800,
                color: "#6b3b21",
                borderColor: "#9f795d",
              }}
            >
              Edit Domain
            </Button>
          )}
        </Box>
      </Paper>

      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: {
            xs: "1fr",
            xl: "0.9fr 1.5fr",
          },
          gap: 2.5,
        }}
      >
        <Paper
          elevation={0}
          sx={{
            minHeight: 600,
            borderRadius: 3,
            border: "1px solid #e9e2da",
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
              Business Entities
            </Typography>

            <Typography
              variant="body2"
              sx={{
                color: "#888888",
              }}
            >
              Select a business concept to
              inspect its semantic profile.
            </Typography>
          </Box>

          <Box
            sx={{
              p: 1.5,
              maxHeight: 700,
              overflowY: "auto",
            }}
          >
            {loadingEntities ? (
              <Box
                sx={{
                  minHeight: 350,
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
            ) : entities.length === 0 ? (
              <EmptyState
                title="No business entities"
                description="Create an entity manually or generate a suggestion from an approved metadata table."
              />
            ) : (
              entities.map((entity) => (
                <EntityListItem
                  key={entity.id}
                  entity={entity}
                  selected={
                    selectedEntity?.id ===
                    entity.id
                  }
                  onClick={() =>
                    setSelectedEntity(
                      entity
                    )
                  }
                />
              ))
            )}
          </Box>
        </Paper>

        <Paper
          elevation={0}
          sx={{
            minHeight: 600,
            borderRadius: 3,
            border: "1px solid #e9e2da",
            overflow: "hidden",
          }}
        >
          {!selectedEntity ? (
            <EmptyState
              title="Select a business entity"
              description="Choose an entity from the left to review its description, governance and physical table mappings."
            />
          ) : (
            <EntityDetails
              entity={selectedEntity}
              metadataTables={
                metadataTables
              }
              onEdit={() =>
                openEditEntity(
                  selectedEntity
                )
              }
              onApprove={() =>
                updateEntityApproval(
                  selectedEntity,
                  "approved"
                )
              }
              onReject={() =>
                updateEntityApproval(
                  selectedEntity,
                  "rejected"
                )
              }
              onMapTable={
                openMappingDialog
              }
              onRemoveMapping={
                removeMapping
              }
            />
          )}
        </Paper>
      </Box>

      <DomainDialog
        open={domainDialogOpen}
        editing={Boolean(
          editingDomain
        )}
        form={domainForm}
        saving={savingDomain}
        onChange={setDomainForm}
        onClose={() =>
          setDomainDialogOpen(false)
        }
        onSave={saveDomain}
      />

      <EntityDialog
        open={entityDialogOpen}
        editing={Boolean(
          editingEntity
        )}
        domains={activeDomains}
        form={entityForm}
        synonymText={synonymText}
        saving={savingEntity}
        onFormChange={setEntityForm}
        onSynonymChange={
          setSynonymText
        }
        onClose={() =>
          setEntityDialogOpen(false)
        }
        onSave={saveEntity}
      />

      <MappingDialog
        open={mappingDialogOpen}
        metadataTables={
          metadataTables
        }
        tableId={mappingTableId}
        mappingType={mappingType}
        confidence={
          mappingConfidence
        }
        saving={savingMapping}
        onTableChange={
          setMappingTableId
        }
        onTypeChange={
          setMappingType
        }
        onConfidenceChange={
          setMappingConfidence
        }
        onClose={() =>
          setMappingDialogOpen(false)
        }
        onSave={saveMapping}
      />

      <SuggestionDialog
        open={suggestionDialogOpen}
        metadataTables={
          metadataTables
        }
        selectedTableId={
          suggestionTableId
        }
        suggestion={suggestion}
        generating={
          generatingSuggestion
        }
        onTableChange={
          setSuggestionTableId
        }
        onGenerate={
          generateSuggestion
        }
        onUse={
          useSuggestion
        }
        onClose={() => {
          setSuggestionDialogOpen(
            false
          );
          setSuggestion(null);
        }}
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


function parseStoredList(
  value: string | null
): string[] {
  if (!value) {
    return [];
  }

  try {
    const parsed = JSON.parse(value);

    if (Array.isArray(parsed)) {
      return parsed.map(String);
    }
  } catch {
    // Fall back to delimited text.
  }

  return value
    .split(/[,;\n]+/)
    .map((item) => item.trim())
    .filter(Boolean);
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
        border: "1px solid #e9e2da",
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
        variant="h5"
        sx={{
          mt: 1,
          color: "#4f2c1a",
          fontWeight: 900,
          overflow: "hidden",
          textOverflow: "ellipsis",
          whiteSpace: "nowrap",
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


function EntityListItem({
  entity,
  selected,
  onClick,
}: {
  entity: BusinessEntity;
  selected: boolean;
  onClick: () => void;
}) {
  return (
    <Box
      onClick={onClick}
      sx={{
        p: 1.7,
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
          borderColor: "#d9bd8a",
        },
      }}
    >
      <Box
        sx={{
          display: "flex",
          justifyContent:
            "space-between",
          alignItems: "flex-start",
          gap: 1,
        }}
      >
        <Box sx={{ minWidth: 0 }}>
          <Typography
            sx={{
              color: "#4f2c1a",
              fontWeight: 900,
            }}
          >
            {entity.name}
          </Typography>

          <Typography
            variant="caption"
            sx={{
              display: "block",
              color: "#888888",
            }}
          >
            {
              entity.table_mappings
                .length
            }{" "}
            physical mapping(s)
          </Typography>
        </Box>

        <StatusChip
          status={
            entity.approval_status
          }
        />
      </Box>

      <LinearProgress
        variant="determinate"
        value={entity.confidence}
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
        {entity.confidence}% semantic
        confidence
      </Typography>
    </Box>
  );
}


function EntityDetails({
  entity,
  metadataTables,
  onEdit,
  onApprove,
  onReject,
  onMapTable,
  onRemoveMapping,
}: {
  entity: BusinessEntity;
  metadataTables:
    MetadataTableSummary[];
  onEdit: () => void;
  onApprove: () => void;
  onReject: () => void;
  onMapTable: () => void;
  onRemoveMapping:
    (mappingId: number) => void;
}) {
  const synonyms =
    parseStoredList(entity.synonyms);

  const findTableName = (
    tableId: number
  ) => {
    const table =
      metadataTables.find(
        (item) =>
          item.id === tableId
      );

    if (!table) {
      return `Table #${tableId}`;
    }

    return table.schema_name
      ? `${table.schema_name}.${table.table_name}`
      : table.table_name;
  };

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
            alignItems: "flex-start",
            flexWrap: "wrap",
            gap: 2,
          }}
        >
          <Box>
            <Typography
              variant="h4"
              sx={{
                fontWeight: 900,
              }}
            >
              {entity.name}
            </Typography>

            <Typography
              sx={{
                mt: 1,
                maxWidth: 680,
                color:
                  "rgba(255,255,255,0.78)",
                lineHeight: 1.7,
              }}
            >
              {entity.description ||
                "No business description has been added."}
            </Typography>
          </Box>

          <Box
            sx={{
              display: "flex",
              flexWrap: "wrap",
              gap: 1,
            }}
          >
            <StatusChip
              status={
                entity.approval_status
              }
            />

            <Button
              variant="contained"
              onClick={onEdit}
              sx={{
                bgcolor: "#ffffff",
                color: "#5b311b",
                textTransform: "none",
                fontWeight: 800,
                "&:hover": {
                  bgcolor: "#fff3dc",
                },
              }}
            >
              Edit Entity
            </Button>
          </Box>
        </Box>

        <Box
          sx={{
            mt: 2.5,
            display: "flex",
            flexWrap: "wrap",
            gap: 1,
          }}
        >
          <Chip
            label={`Classification: ${entity.classification}`}
            sx={{
              bgcolor:
                "rgba(255,255,255,0.14)",
              color: "#ffffff",
              textTransform:
                "capitalize",
            }}
          />

          <Chip
            label={
              entity.ai_access_allowed
                ? "AI Access Allowed"
                : "AI Access Blocked"
            }
            sx={{
              bgcolor:
                entity.ai_access_allowed
                  ? "rgba(55,180,105,0.28)"
                  : "rgba(220,75,75,0.28)",
              color: "#ffffff",
            }}
          />

          <Chip
            label={`Owner: ${
              entity.business_owner ||
              "Not assigned"
            }`}
            sx={{
              bgcolor:
                "rgba(255,255,255,0.14)",
              color: "#ffffff",
            }}
          />
        </Box>
      </Box>

      <Box sx={{ p: 3 }}>
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: {
              xs: "1fr",
              md: "repeat(2, 1fr)",
            },
            gap: 2,
          }}
        >
          <InfoPanel
            title="Business Vocabulary"
          >
            {synonyms.length ? (
              <Box
                sx={{
                  display: "flex",
                  flexWrap: "wrap",
                  gap: 0.8,
                }}
              >
                {synonyms.map(
                  (synonym) => (
                    <Chip
                      key={synonym}
                      label={synonym}
                      size="small"
                      sx={{
                        bgcolor:
                          "#fff3dc",
                        color:
                          "#765019",
                      }}
                    />
                  )
                )}
              </Box>
            ) : (
              <Typography
                variant="body2"
                sx={{
                  color: "#888888",
                }}
              >
                No synonyms have been added.
              </Typography>
            )}
          </InfoPanel>

          <InfoPanel
            title="Semantic Confidence"
          >
            <Typography
              variant="h4"
              sx={{
                color: "#4f2c1a",
                fontWeight: 900,
              }}
            >
              {entity.confidence}%
            </Typography>

            <LinearProgress
              variant="determinate"
              value={
                entity.confidence
              }
              sx={{
                mt: 1.5,
                height: 8,
                borderRadius: 5,
              }}
            />
          </InfoPanel>
        </Box>

        <Box
          sx={{
            mt: 3,
            display: "flex",
            justifyContent:
              "space-between",
            alignItems: "center",
            flexWrap: "wrap",
            gap: 2,
          }}
        >
          <Box>
            <Typography
              variant="h6"
              sx={{
                color: "#4f2c1a",
                fontWeight: 900,
              }}
            >
              Physical Data Mappings
            </Typography>

            <Typography
              variant="body2"
              sx={{
                color: "#888888",
              }}
            >
              Tables representing this
              business concept across
              connected systems.
            </Typography>
          </Box>

          <Button
            variant="outlined"
            onClick={onMapTable}
            sx={{
              textTransform: "none",
              fontWeight: 800,
              color: "#6b3b21",
              borderColor: "#9f795d",
            }}
          >
            Map Physical Table
          </Button>
        </Box>

        <Box
          sx={{
            mt: 2,
            display: "grid",
            gap: 1.3,
          }}
        >
          {entity.table_mappings.length ===
          0 ? (
            <Alert severity="info">
              This business entity has not
              yet been mapped to a physical
              table.
            </Alert>
          ) : (
            entity.table_mappings.map(
              (mapping) => (
                <Paper
                  key={mapping.id}
                  elevation={0}
                  sx={{
                    p: 2,
                    borderRadius: 2.5,
                    bgcolor: "#faf8f5",
                    border:
                      "1px solid #ece5dd",
                    display: "flex",
                    justifyContent:
                      "space-between",
                    alignItems:
                      "center",
                    flexWrap: "wrap",
                    gap: 2,
                  }}
                >
                  <Box>
                    <Typography
                      sx={{
                        color:
                          "#4f2c1a",
                        fontWeight: 800,
                      }}
                    >
                      {findTableName(
                        mapping.metadata_table_id
                      )}
                    </Typography>

                    <Typography
                      variant="caption"
                      sx={{
                        color:
                          "#888888",
                      }}
                    >
                      {mapping.mapping_type}{" "}
                      mapping ·{" "}
                      {mapping.confidence}%
                      confidence
                    </Typography>
                  </Box>

                  <Button
                    size="small"
                    color="error"
                    onClick={() =>
                      onRemoveMapping(
                        mapping.id
                      )
                    }
                    sx={{
                      textTransform:
                        "none",
                    }}
                  >
                    Remove
                  </Button>
                </Paper>
              )
            )
          )}
        </Box>

        <Box
          sx={{
            mt: 3,
            pt: 2.5,
            borderTop:
              "1px solid #eee7df",
            display: "flex",
            justifyContent:
              "flex-end",
            flexWrap: "wrap",
            gap: 1,
          }}
        >
          <Button
            variant="outlined"
            color="error"
            onClick={onReject}
            sx={{
              textTransform: "none",
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
              textTransform: "none",
              fontWeight: 800,
              "&:hover": {
                bgcolor: "#1f623d",
              },
            }}
          >
            Approve Entity
          </Button>
        </Box>
      </Box>
    </>
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
        border: "1px solid #ece5dd",
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


function DomainDialog({
  open,
  editing,
  form,
  saving,
  onChange,
  onClose,
  onSave,
}: {
  open: boolean;
  editing: boolean;
  form: BusinessDomainCreate;
  saving: boolean;
  onChange:
    React.Dispatch<
      React.SetStateAction<BusinessDomainCreate>
    >;
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
      maxWidth="sm"
    >
      <DialogTitle
        sx={{
          color: "#4f2c1a",
          fontWeight: 900,
        }}
      >
        {editing
          ? "Edit Business Domain"
          : "Create Business Domain"}
      </DialogTitle>

      <DialogContent dividers>
        <Box
          sx={{
            display: "grid",
            gap: 2,
          }}
        >
          <TextField
            label="Domain name"
            value={form.name}
            onChange={(event) =>
              onChange((current) => ({
                ...current,
                name:
                  event.target.value,
              }))
            }
          />

          <TextField
            multiline
            minRows={3}
            label="Description"
            value={
              form.description ?? ""
            }
            onChange={(event) =>
              onChange((current) => ({
                ...current,
                description:
                  event.target.value,
              }))
            }
          />

          <TextField
            label="Department"
            value={
              form.department ?? ""
            }
            onChange={(event) =>
              onChange((current) => ({
                ...current,
                department:
                  event.target.value,
              }))
            }
          />

          <TextField
            label="Business owner"
            value={form.owner ?? ""}
            onChange={(event) =>
              onChange((current) => ({
                ...current,
                owner:
                  event.target.value,
              }))
            }
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
            : "Save Domain"}
        </Button>
      </DialogActions>
    </Dialog>
  );
}


function EntityDialog({
  open,
  editing,
  domains,
  form,
  synonymText,
  saving,
  onFormChange,
  onSynonymChange,
  onClose,
  onSave,
}: {
  open: boolean;
  editing: boolean;
  domains: BusinessDomain[];
  form: BusinessEntityCreate;
  synonymText: string;
  saving: boolean;
  onFormChange:
    React.Dispatch<
      React.SetStateAction<BusinessEntityCreate>
    >;
  onSynonymChange:
    (value: string) => void;
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
          ? "Edit Business Entity"
          : "Create Business Entity"}
      </DialogTitle>

      <DialogContent dividers>
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: {
              xs: "1fr",
              md: "repeat(2, 1fr)",
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
              value={form.domain_id || ""}
              onChange={(event) =>
                onFormChange(
                  (current) => ({
                    ...current,
                    domain_id: Number(
                      event.target.value
                    ),
                  })
                )
              }
            >
              {domains.map((domain) => (
                <MenuItem
                  key={domain.id}
                  value={domain.id}
                >
                  {domain.name}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <TextField
            label="Entity name"
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
            placeholder="Example: Customer"
          />

          <TextField
            label="Business owner"
            value={
              form.business_owner ??
              ""
            }
            onChange={(event) =>
              onFormChange(
                (current) => ({
                  ...current,
                  business_owner:
                    event.target.value,
                })
              )
            }
          />

          <FormControl fullWidth>
            <InputLabel>
              Classification
            </InputLabel>

            <Select
              label="Classification"
              value={
                form.classification
              }
              onChange={(event) =>
                onFormChange(
                  (current) => ({
                    ...current,
                    classification:
                      event.target
                        .value as EntityClassification,
                  })
                )
              }
            >
              <MenuItem value="public">
                Public
              </MenuItem>

              <MenuItem value="internal">
                Internal
              </MenuItem>

              <MenuItem value="confidential">
                Confidential
              </MenuItem>

              <MenuItem value="restricted">
                Restricted
              </MenuItem>
            </Select>
          </FormControl>

          <TextField
            label="Semantic confidence"
            type="number"
            value={form.confidence}
            onChange={(event) =>
              onFormChange(
                (current) => ({
                  ...current,
                  confidence: Math.max(
                    0,
                    Math.min(
                      100,
                      Number(
                        event.target.value
                      )
                    )
                  ),
                })
              )
            }
          />

          <Box
            sx={{
              px: 1,
              display: "flex",
              alignItems: "center",
            }}
          >
            <FormControlLabel
              control={
                <Switch
                  checked={
                    form.ai_access_allowed
                  }
                  onChange={(event) =>
                    onFormChange(
                      (current) => ({
                        ...current,
                        ai_access_allowed:
                          event.target.checked,
                      })
                    )
                  }
                />
              }
              label="Allow AI access"
            />
          </Box>

          <TextField
            multiline
            minRows={4}
            label="Business description"
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

          <TextField
            multiline
            minRows={3}
            label="Synonyms"
            value={synonymText}
            onChange={(event) =>
              onSynonymChange(
                event.target.value
              )
            }
            helperText="Separate terms using commas, semicolons or new lines."
            sx={{
              gridColumn: {
                xs: "auto",
                md: "1 / -1",
              },
            }}
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
            : "Save Entity"}
        </Button>
      </DialogActions>
    </Dialog>
  );
}


function MappingDialog({
  open,
  metadataTables,
  tableId,
  mappingType,
  confidence,
  saving,
  onTableChange,
  onTypeChange,
  onConfidenceChange,
  onClose,
  onSave,
}: {
  open: boolean;
  metadataTables:
    MetadataTableSummary[];
  tableId: number | "";
  mappingType: EntityMappingType;
  confidence: number;
  saving: boolean;
  onTableChange:
    (value: number | "") => void;
  onTypeChange:
    (value: EntityMappingType) => void;
  onConfidenceChange:
    (value: number) => void;
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
      maxWidth="sm"
    >
      <DialogTitle
        sx={{
          color: "#4f2c1a",
          fontWeight: 900,
        }}
      >
        Map Physical Table
      </DialogTitle>

      <DialogContent dividers>
        <Box
          sx={{
            display: "grid",
            gap: 2,
          }}
        >
          <FormControl fullWidth>
            <InputLabel>
              Metadata table
            </InputLabel>

            <Select
              label="Metadata table"
              value={tableId}
              onChange={(event) =>
                onTableChange(
                  Number(
                    event.target.value
                  )
                )
              }
            >
              {metadataTables.map(
                (table) => (
                  <MenuItem
                    key={table.id}
                    value={table.id}
                  >
                    {table.business_name ||
                      table.table_name}
                    {" — "}
                    {table.schema_name
                      ? `${table.schema_name}.${table.table_name}`
                      : table.table_name}
                  </MenuItem>
                )
              )}
            </Select>
          </FormControl>

          <FormControl fullWidth>
            <InputLabel>
              Mapping type
            </InputLabel>

            <Select
              label="Mapping type"
              value={mappingType}
              onChange={(event) =>
                onTypeChange(
                  event.target
                    .value as EntityMappingType
                )
              }
            >
              <MenuItem value="primary">
                Primary
              </MenuItem>

              <MenuItem value="supporting">
                Supporting
              </MenuItem>

              <MenuItem value="reference">
                Reference
              </MenuItem>
            </Select>
          </FormControl>

          <TextField
            label="Mapping confidence"
            type="number"
            value={confidence}
            onChange={(event) =>
              onConfidenceChange(
                Math.max(
                  0,
                  Math.min(
                    100,
                    Number(
                      event.target.value
                    )
                  )
                )
              )
            }
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
          disabled={
            saving ||
            tableId === ""
          }
          onClick={onSave}
          sx={{
            textTransform: "none",
            fontWeight: 800,
            background:
              "linear-gradient(90deg, #61351f, #c78f2b)",
          }}
        >
          {saving
            ? "Mapping..."
            : "Create Mapping"}
        </Button>
      </DialogActions>
    </Dialog>
  );
}


function SuggestionDialog({
  open,
  metadataTables,
  selectedTableId,
  suggestion,
  generating,
  onTableChange,
  onGenerate,
  onUse,
  onClose,
}: {
  open: boolean;
  metadataTables:
    MetadataTableSummary[];
  selectedTableId: number | "";
  suggestion:
    BusinessEntitySuggestion | null;
  generating: boolean;
  onTableChange:
    (value: number | "") => void;
  onGenerate: () => void;
  onUse: () => void;
  onClose: () => void;
}) {
  return (
    <Dialog
      open={open}
      onClose={() => {
        if (!generating) {
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
        Generate Business Entity Suggestion
      </DialogTitle>

      <DialogContent dividers>
        <FormControl fullWidth>
          <InputLabel>
            Approved metadata table
          </InputLabel>

          <Select
            label="Approved metadata table"
            value={selectedTableId}
            onChange={(event) =>
              onTableChange(
                Number(
                  event.target.value
                )
              )
            }
          >
            {metadataTables.map(
              (table) => (
                <MenuItem
                  key={table.id}
                  value={table.id}
                >
                  {table.business_name ||
                    table.table_name}
                  {" — "}
                  {table.table_name}
                </MenuItem>
              )
            )}
          </Select>
        </FormControl>

        <Box
          sx={{
            mt: 2,
            display: "flex",
            justifyContent:
              "flex-end",
          }}
        >
          <Button
            variant="contained"
            disabled={
              generating ||
              selectedTableId === ""
            }
            onClick={onGenerate}
            sx={{
              textTransform: "none",
              fontWeight: 800,
              background:
                "linear-gradient(90deg, #61351f, #c78f2b)",
            }}
          >
            {generating ? (
              <>
                <CircularProgress
                  size={18}
                  color="inherit"
                  sx={{ mr: 1 }}
                />
                Analysing...
              </>
            ) : (
              "Generate Suggestion"
            )}
          </Button>
        </Box>

        {suggestion && (
          <Paper
            elevation={0}
            sx={{
              mt: 3,
              p: 3,
              borderRadius: 3,
              border:
                "1px solid #e9e2da",
              bgcolor: "#faf8f5",
            }}
          >
            <Typography
              variant="caption"
              sx={{
                color: "#888888",
                fontWeight: 800,
              }}
            >
              SUGGESTED BUSINESS DOMAIN
            </Typography>

            <Typography
              variant="h6"
              sx={{
                color: "#4f2c1a",
                fontWeight: 900,
              }}
            >
              {
                suggestion.suggested_domain_name
              }
            </Typography>

            <Typography
              variant="caption"
              sx={{
                display: "block",
                mt: 2,
                color: "#888888",
                fontWeight: 800,
              }}
            >
              SUGGESTED BUSINESS ENTITY
            </Typography>

            <Typography
              variant="h4"
              sx={{
                color: "#4f2c1a",
                fontWeight: 900,
              }}
            >
              {
                suggestion.suggested_entity_name
              }
            </Typography>

            <Typography
              sx={{
                mt: 2,
                color: "#666666",
                lineHeight: 1.7,
              }}
            >
              {suggestion.description}
            </Typography>

            <Box
              sx={{
                mt: 2,
                display: "flex",
                flexWrap: "wrap",
                gap: 0.8,
              }}
            >
              {suggestion.synonyms.map(
                (synonym) => (
                  <Chip
                    key={synonym}
                    label={synonym}
                    size="small"
                    sx={{
                      bgcolor:
                        "#fff3dc",
                      color:
                        "#765019",
                    }}
                  />
                )
              )}
            </Box>

            <Typography
              sx={{
                mt: 2.5,
                color: "#4f2c1a",
                fontWeight: 900,
              }}
            >
              Confidence:{" "}
              {suggestion.confidence}%
            </Typography>

            <LinearProgress
              variant="determinate"
              value={
                suggestion.confidence
              }
              sx={{
                mt: 1,
                height: 8,
                borderRadius: 5,
              }}
            />

            <Box sx={{ mt: 2 }}>
              {suggestion.reasons.map(
                (reason) => (
                  <Typography
                    key={reason}
                    variant="body2"
                    sx={{
                      mb: 0.7,
                      color: "#555555",
                    }}
                  >
                    ✓ {reason}
                  </Typography>
                )
              )}
            </Box>
          </Paper>
        )}
      </DialogContent>

      <DialogActions
        sx={{
          px: 3,
          py: 2,
        }}
      >
        <Button
          disabled={generating}
          onClick={onClose}
          sx={{
            textTransform: "none",
          }}
        >
          Close
        </Button>

        {suggestion && (
          <Button
            variant="contained"
            disabled={generating}
            onClick={onUse}
            sx={{
              textTransform: "none",
              fontWeight: 800,
              background:
                "linear-gradient(90deg, #61351f, #c78f2b)",
            }}
          >
            Use This Suggestion
          </Button>
        )}
      </DialogActions>
    </Dialog>
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
            fontSize: "1.2rem",
          }}
        >
          BE
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
            maxWidth: 430,
          }}
        >
          {description}
        </Typography>
      </Box>
    </Box>
  );
}


function StatusChip({
  status,
}: {
  status: string;
}) {
  const settings: Record<
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
        color: selected.color,
        fontWeight: 800,
      }}
    />
  );
}


export default BusinessEntityRegistryPage;
