import {
  Alert,
  Box,
  Button,
  Checkbox,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  InputLabel,
  LinearProgress,
  ListItemText,
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
  createBusinessCapability,
  createCapabilityEntityMapping,
  deleteBusinessCapability,
  deleteCapabilityEntityMapping,
  getBusinessCapabilities,
  suggestBusinessCapability,
  updateBusinessCapability,
} from "../../services/businessCapabilities";

import {
  getBusinessDomains,
  getBusinessEntities,
} from "../../services/businessEntities";

import type {
  BusinessDomain,
  BusinessEntity,
} from "../../types/businessEntity";

import type {
  BusinessCapability,
  BusinessCapabilityCreate,
  CapabilityApprovalStatus,
  CapabilityEntityMappingRole,
  CapabilityMaturityLevel,
  CapabilitySuggestion,
  CapabilityType,
} from "../../types/businessCapability";


function BusinessCapabilityRegistryPage() {
  const [domains, setDomains] =
    useState<BusinessDomain[]>([]);

  const [entities, setEntities] =
    useState<BusinessEntity[]>([]);

  const [capabilities, setCapabilities] =
    useState<BusinessCapability[]>([]);

  const [selectedDomainId, setSelectedDomainId] =
    useState<number | "">("");

  const [selectedCapability, setSelectedCapability] =
    useState<BusinessCapability | null>(null);

  const [approvalFilter, setApprovalFilter] =
    useState("");

  const [loading, setLoading] =
    useState(true);

  const [loadingCapabilities, setLoadingCapabilities] =
    useState(false);

  const [capabilityDialogOpen, setCapabilityDialogOpen] =
    useState(false);

  const [mappingDialogOpen, setMappingDialogOpen] =
    useState(false);

  const [suggestionDialogOpen, setSuggestionDialogOpen] =
    useState(false);

  const [editingCapability, setEditingCapability] =
    useState<BusinessCapability | null>(null);

  const [savingCapability, setSavingCapability] =
    useState(false);

  const [savingMapping, setSavingMapping] =
    useState(false);

  const [generatingSuggestion, setGeneratingSuggestion] =
    useState(false);

  const [suggestion, setSuggestion] =
    useState<CapabilitySuggestion | null>(null);

  const [suggestionEntityIds, setSuggestionEntityIds] =
    useState<number[]>([]);

  const [mappingEntityId, setMappingEntityId] =
    useState<number | "">("");

  const [mappingRole, setMappingRole] =
    useState<CapabilityEntityMappingRole>("primary");

  const [mappingConfidence, setMappingConfidence] =
    useState(100);

  const [message, setMessage] =
    useState("");

  const [messageType, setMessageType] =
    useState<"success" | "error">("success");

  const [capabilityForm, setCapabilityForm] =
    useState<BusinessCapabilityCreate>({
      domain_id: 0,
      parent_capability_id: null,
      name: "",
      description: "",
      business_owner: "",
      capability_type: "operational",
      maturity_level: "developing",
      confidence: 0,
    });


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
        capabilityResult,
      ] = await Promise.all([
        getBusinessDomains(),
        getBusinessEntities(),
        getBusinessCapabilities(),
      ]);

      const activeDomains =
        domainResult.filter(
          (domain) => domain.is_active
        );

      setDomains(activeDomains);
      setEntities(entityResult);
      setCapabilities(capabilityResult);

      if (activeDomains.length > 0) {
        setSelectedDomainId(
          activeDomains[0].id
        );
      }
    } catch (error: any) {
      showMessage(
        error?.response?.data?.detail ??
          "Unable to load the Business Capability Registry.",
        "error"
      );
    } finally {
      setLoading(false);
    }
  };


  const loadCapabilities = async () => {
    if (selectedDomainId === "") {
      setCapabilities([]);
      return;
    }

    try {
      setLoadingCapabilities(true);

      const result =
        await getBusinessCapabilities(
          selectedDomainId,
          approvalFilter || undefined
        );

      setCapabilities(result);
      setSelectedCapability(null);
    } catch (error: any) {
      showMessage(
        error?.response?.data?.detail ??
          "Unable to load business capabilities.",
        "error"
      );
    } finally {
      setLoadingCapabilities(false);
    }
  };


  useEffect(() => {
    loadInitialData();
  }, []);


  useEffect(() => {
    if (!loading) {
      loadCapabilities();
    }
  }, [
    selectedDomainId,
    approvalFilter,
  ]);


  const selectedDomain =
    domains.find(
      (domain) =>
        domain.id === selectedDomainId
    ) ?? null;


  const domainEntities = useMemo(() => {
    if (selectedDomainId === "") {
      return [];
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


  const approvedCount = useMemo(
    () =>
      capabilities.filter(
        (capability) =>
          capability.approval_status ===
          "approved"
      ).length,
    [capabilities]
  );


  const mappedCount = useMemo(
    () =>
      capabilities.filter(
        (capability) =>
          capability.entity_mappings.length > 0
      ).length,
    [capabilities]
  );


  const averageMaturity = useMemo(() => {
    if (!capabilities.length) {
      return "No Data";
    }

    const maturityScores: Record<
      CapabilityMaturityLevel,
      number
    > = {
      initial: 1,
      developing: 2,
      defined: 3,
      managed: 4,
      optimized: 5,
    };

    const average =
      capabilities.reduce(
        (total, capability) =>
          total +
          maturityScores[
            capability.maturity_level
          ],
        0
      ) / capabilities.length;

    if (average >= 4.5) {
      return "Optimized";
    }

    if (average >= 3.5) {
      return "Managed";
    }

    if (average >= 2.5) {
      return "Defined";
    }

    if (average >= 1.5) {
      return "Developing";
    }

    return "Initial";
  }, [capabilities]);


  const openCreateCapability = () => {
    if (selectedDomainId === "") {
      showMessage(
        "Select a business domain first.",
        "error"
      );
      return;
    }

    setEditingCapability(null);

    setCapabilityForm({
      domain_id: selectedDomainId,
      parent_capability_id: null,
      name: "",
      description: "",
      business_owner:
        selectedDomain?.owner ?? "",
      capability_type: "operational",
      maturity_level: "developing",
      confidence: 0,
    });

    setCapabilityDialogOpen(true);
  };


  const openEditCapability = (
    capability: BusinessCapability
  ) => {
    setEditingCapability(capability);

    setCapabilityForm({
      domain_id: capability.domain_id,
      parent_capability_id:
        capability.parent_capability_id,
      name: capability.name,
      description:
        capability.description ?? "",
      business_owner:
        capability.business_owner ?? "",
      capability_type:
        capability.capability_type,
      maturity_level:
        capability.maturity_level,
      confidence:
        capability.confidence,
    });

    setCapabilityDialogOpen(true);
  };


  const saveCapability = async () => {
    if (
      !capabilityForm.domain_id ||
      !capabilityForm.name.trim()
    ) {
      showMessage(
        "Domain and capability name are required.",
        "error"
      );
      return;
    }

    try {
      setSavingCapability(true);

      const payload = {
        ...capabilityForm,
        name:
          capabilityForm.name.trim(),
        description:
          capabilityForm.description?.trim() ||
          null,
        business_owner:
          capabilityForm.business_owner?.trim() ||
          null,
      };

      if (editingCapability) {
        const updated =
          await updateBusinessCapability(
            editingCapability.id,
            payload
          );

        setCapabilities((current) =>
          current.map((capability) =>
            capability.id === updated.id
              ? updated
              : capability
          )
        );

        setSelectedCapability(updated);

        showMessage(
          "Business capability updated successfully.",
          "success"
        );
      } else {
        const created =
          await createBusinessCapability(
            payload
          );

        setCapabilities((current) =>
          [...current, created].sort(
            (a, b) =>
              a.name.localeCompare(b.name)
          )
        );

        setSelectedCapability(created);

        showMessage(
          "Business capability created successfully.",
          "success"
        );
      }

      setCapabilityDialogOpen(false);
    } catch (error: any) {
      showMessage(
        error?.response?.data?.detail ??
          "Unable to save business capability.",
        "error"
      );
    } finally {
      setSavingCapability(false);
    }
  };


  const updateApproval = async (
    capability: BusinessCapability,
    approvalStatus: CapabilityApprovalStatus
  ) => {
    try {
      const updated =
        await updateBusinessCapability(
          capability.id,
          {
            approval_status:
              approvalStatus,
          }
        );

      updateCapabilityState(updated);

      showMessage(
        approvalStatus === "approved"
          ? "Business capability approved."
          : approvalStatus === "rejected"
            ? "Business capability rejected."
            : "Capability status updated.",
        approvalStatus === "rejected"
          ? "error"
          : "success"
      );
    } catch (error: any) {
      showMessage(
        error?.response?.data?.detail ??
          "Unable to update capability approval.",
        "error"
      );
    }
  };


  const toggleCapabilityActive = async (
    capability: BusinessCapability
  ) => {
    try {
      const updated =
        await updateBusinessCapability(
          capability.id,
          {
            is_active:
              !capability.is_active,
          }
        );

      updateCapabilityState(updated);

      showMessage(
        updated.is_active
          ? "Capability enabled."
          : "Capability disabled.",
        "success"
      );
    } catch (error: any) {
      showMessage(
        error?.response?.data?.detail ??
          "Unable to update capability status.",
        "error"
      );
    }
  };


  const updateCapabilityState = (
    updated: BusinessCapability
  ) => {
    setCapabilities((current) =>
      current.map((capability) =>
        capability.id === updated.id
          ? updated
          : capability
      )
    );

    if (
      selectedCapability?.id ===
      updated.id
    ) {
      setSelectedCapability(updated);
    }
  };


  const removeCapability = async (
    capabilityId: number
  ) => {
    const confirmed = window.confirm(
      "Delete this business capability?"
    );

    if (!confirmed) {
      return;
    }

    try {
      await deleteBusinessCapability(
        capabilityId
      );

      setCapabilities((current) =>
        current.filter(
          (capability) =>
            capability.id !==
            capabilityId
        )
      );

      setSelectedCapability(null);

      showMessage(
        "Business capability deleted.",
        "success"
      );
    } catch (error: any) {
      showMessage(
        error?.response?.data?.detail ??
          "Unable to delete business capability.",
        "error"
      );
    }
  };


  const openMappingDialog = () => {
    if (!selectedCapability) {
      return;
    }

    setMappingEntityId("");
    setMappingRole("primary");
    setMappingConfidence(100);
    setMappingDialogOpen(true);
  };


  const saveMapping = async () => {
    if (
      !selectedCapability ||
      mappingEntityId === ""
    ) {
      showMessage(
        "Select a business entity.",
        "error"
      );
      return;
    }

    try {
      setSavingMapping(true);

      const created =
        await createCapabilityEntityMapping(
          selectedCapability.id,
          {
            business_entity_id:
              mappingEntityId,
            mapping_role:
              mappingRole,
            confidence:
              mappingConfidence,
          }
        );

      const updatedCapability = {
        ...selectedCapability,
        entity_mappings: [
          ...selectedCapability.entity_mappings,
          created,
        ],
      };

      updateCapabilityState(
        updatedCapability
      );

      setMappingDialogOpen(false);

      showMessage(
        "Business entity mapped successfully.",
        "success"
      );
    } catch (error: any) {
      showMessage(
        error?.response?.data?.detail ??
          "Unable to create entity mapping.",
        "error"
      );
    } finally {
      setSavingMapping(false);
    }
  };


  const removeMapping = async (
    mappingId: number
  ) => {
    if (!selectedCapability) {
      return;
    }

    try {
      await deleteCapabilityEntityMapping(
        mappingId
      );

      const updatedCapability = {
        ...selectedCapability,
        entity_mappings:
          selectedCapability.entity_mappings.filter(
            (mapping) =>
              mapping.id !== mappingId
          ),
      };

      updateCapabilityState(
        updatedCapability
      );

      showMessage(
        "Entity mapping removed.",
        "success"
      );
    } catch (error: any) {
      showMessage(
        error?.response?.data?.detail ??
          "Unable to remove entity mapping.",
        "error"
      );
    }
  };


  const openSuggestionDialog = () => {
    if (selectedDomainId === "") {
      showMessage(
        "Select a business domain first.",
        "error"
      );
      return;
    }

    setSuggestion(null);
    setSuggestionEntityIds([]);
    setSuggestionDialogOpen(true);
  };


  const generateSuggestion = async () => {
    if (
      selectedDomainId === "" ||
      suggestionEntityIds.length === 0
    ) {
      showMessage(
        "Select at least one business entity.",
        "error"
      );
      return;
    }

    try {
      setGeneratingSuggestion(true);

      const result =
        await suggestBusinessCapability(
          selectedDomainId,
          suggestionEntityIds
        );

      setSuggestion(result);
    } catch (error: any) {
      showMessage(
        error?.response?.data?.detail ??
          "Unable to generate capability suggestion.",
        "error"
      );
    } finally {
      setGeneratingSuggestion(false);
    }
  };


  const useSuggestion = () => {
    if (
      !suggestion ||
      selectedDomainId === ""
    ) {
      return;
    }

    setEditingCapability(null);

    setCapabilityForm({
      domain_id: selectedDomainId,
      parent_capability_id: null,
      name:
        suggestion.suggested_name,
      description:
        suggestion.description,
      business_owner:
        selectedDomain?.owner ?? "",
      capability_type:
        suggestion.capability_type,
      maturity_level:
        suggestion.maturity_level,
      confidence:
        suggestion.confidence,
    });

    setSuggestionDialogOpen(false);
    setCapabilityDialogOpen(true);
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
            Loading business capabilities...
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
            Business Capability Registry
          </Typography>

          <Typography
            sx={{
              mt: 0.7,
              color: "#777777",
            }}
          >
            Organize business entities into governed
            enterprise functions and capabilities.
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
            Generate Suggestion
          </Button>

          <Button
            variant="contained"
            onClick={openCreateCapability}
            sx={{
              textTransform: "none",
              fontWeight: 800,
              background:
                "linear-gradient(90deg, #61351f, #c78f2b)",
            }}
          >
            New Capability
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
          label="Approved Capabilities"
          value={String(approvedCount)}
          description="Trusted functions available to NIBGPT"
        />

        <SummaryCard
          label="Mapped Capabilities"
          value={String(mappedCount)}
          description="Capabilities linked to approved entities"
        />

        <SummaryCard
          label="Average Maturity"
          value={averageMaturity}
          description="Current maturity across the selected domain"
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
              md: "repeat(2, minmax(0, 1fr))",
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
              onChange={(event) =>
                setSelectedDomainId(
                  Number(
                    event.target.value
                  )
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
            xl: "0.9fr 1.5fr",
          },
          gap: 2.5,
        }}
      >
        <Paper
          elevation={0}
          sx={{
            minHeight: 620,
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
              Domain Capabilities
            </Typography>

            <Typography
              variant="body2"
              sx={{ color: "#888888" }}
            >
              Select a capability to inspect its
              maturity and business entities.
            </Typography>
          </Box>

          <Box
            sx={{
              p: 1.5,
              maxHeight: 730,
              overflowY: "auto",
            }}
          >
            {loadingCapabilities ? (
              <Box
                sx={{
                  minHeight: 350,
                  display: "grid",
                  placeItems: "center",
                }}
              >
                <CircularProgress
                  sx={{ color: "#a97826" }}
                />
              </Box>
            ) : capabilities.length === 0 ? (
              <EmptyState
                title="No business capabilities"
                description="Create a capability manually or generate a suggestion from approved business entities."
              />
            ) : (
              capabilities.map(
                (capability) => (
                  <CapabilityListItem
                    key={capability.id}
                    capability={capability}
                    selected={
                      selectedCapability?.id ===
                      capability.id
                    }
                    parentName={
                      capabilities.find(
                        (item) =>
                          item.id ===
                          capability.parent_capability_id
                      )?.name ?? null
                    }
                    onClick={() =>
                      setSelectedCapability(
                        capability
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
            border: "1px solid #e9e2da",
            overflow: "hidden",
          }}
        >
          {!selectedCapability ? (
            <EmptyState
              title="Select a business capability"
              description="Choose a capability to review its profile, hierarchy, maturity and mapped entities."
            />
          ) : (
            <CapabilityDetails
              capability={selectedCapability}
              capabilities={capabilities}
              entities={domainEntities}
              onEdit={() =>
                openEditCapability(
                  selectedCapability
                )
              }
              onApprove={() =>
                updateApproval(
                  selectedCapability,
                  "approved"
                )
              }
              onReject={() =>
                updateApproval(
                  selectedCapability,
                  "rejected"
                )
              }
              onToggleActive={() =>
                toggleCapabilityActive(
                  selectedCapability
                )
              }
              onDelete={() =>
                removeCapability(
                  selectedCapability.id
                )
              }
              onMapEntity={
                openMappingDialog
              }
              onRemoveMapping={
                removeMapping
              }
            />
          )}
        </Paper>
      </Box>

      <CapabilityDialog
        open={capabilityDialogOpen}
        editing={Boolean(
          editingCapability
        )}
        form={capabilityForm}
        capabilities={capabilities}
        saving={savingCapability}
        onFormChange={
          setCapabilityForm
        }
        onClose={() =>
          setCapabilityDialogOpen(
            false
          )
        }
        onSave={saveCapability}
      />

      <EntityMappingDialog
        open={mappingDialogOpen}
        entities={domainEntities}
        selectedEntityId={
          mappingEntityId
        }
        mappingRole={mappingRole}
        confidence={
          mappingConfidence
        }
        saving={savingMapping}
        onEntityChange={
          setMappingEntityId
        }
        onRoleChange={
          setMappingRole
        }
        onConfidenceChange={
          setMappingConfidence
        }
        onClose={() =>
          setMappingDialogOpen(false)
        }
        onSave={saveMapping}
      />

      <CapabilitySuggestionDialog
        open={suggestionDialogOpen}
        entities={domainEntities}
        selectedEntityIds={
          suggestionEntityIds
        }
        suggestion={suggestion}
        generating={
          generatingSuggestion
        }
        onEntitiesChange={
          setSuggestionEntityIds
        }
        onGenerate={
          generateSuggestion
        }
        onUse={useSuggestion}
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
        variant="h4"
        sx={{
          mt: 1,
          color: "#4f2c1a",
          fontWeight: 900,
          textTransform: "capitalize",
        }}
      >
        {value}
      </Typography>

      <Typography
        variant="caption"
        sx={{ color: "#999999" }}
      >
        {description}
      </Typography>
    </Paper>
  );
}


function CapabilityListItem({
  capability,
  selected,
  parentName,
  onClick,
}: {
  capability: BusinessCapability;
  selected: boolean;
  parentName: string | null;
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
            {capability.name}
          </Typography>

          <Typography
            variant="caption"
            sx={{
              display: "block",
              color: "#888888",
            }}
          >
            {parentName
              ? `Parent: ${parentName}`
              : "Top-level capability"}
          </Typography>
        </Box>

        <CapabilityStatusChip
          status={
            capability.approval_status
          }
        />
      </Box>

      <Box
        sx={{
          mt: 1.2,
          display: "flex",
          flexWrap: "wrap",
          gap: 0.7,
        }}
      >
        <Chip
          label={capability.capability_type}
          size="small"
          sx={{
            textTransform: "capitalize",
          }}
        />

        <Chip
          label={capability.maturity_level}
          size="small"
          sx={{
            textTransform: "capitalize",
            bgcolor: "#fff3dc",
            color: "#765019",
          }}
        />

        <Chip
          label={`${capability.entity_mappings.length} entities`}
          size="small"
        />
      </Box>

      <LinearProgress
        variant="determinate"
        value={capability.confidence}
        sx={{
          mt: 1.4,
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
        {capability.confidence}% confidence
      </Typography>
    </Box>
  );
}


function CapabilityDetails({
  capability,
  capabilities,
  entities,
  onEdit,
  onApprove,
  onReject,
  onToggleActive,
  onDelete,
  onMapEntity,
  onRemoveMapping,
}: {
  capability: BusinessCapability;
  capabilities: BusinessCapability[];
  entities: BusinessEntity[];
  onEdit: () => void;
  onApprove: () => void;
  onReject: () => void;
  onToggleActive: () => void;
  onDelete: () => void;
  onMapEntity: () => void;
  onRemoveMapping:
    (mappingId: number) => void;
}) {
  const parentCapability =
    capabilities.find(
      (item) =>
        item.id ===
        capability.parent_capability_id
    ) ?? null;

  const childCapabilities =
    capabilities.filter(
      (item) =>
        item.parent_capability_id ===
        capability.id
    );

  const findEntityName = (
    entityId: number
  ) =>
    entities.find(
      (entity) =>
        entity.id === entityId
    )?.name ?? `Entity #${entityId}`;

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
              {capability.name}
            </Typography>

            <Typography
              sx={{
                mt: 1,
                maxWidth: 700,
                color:
                  "rgba(255,255,255,0.78)",
                lineHeight: 1.7,
              }}
            >
              {capability.description ||
                "No business capability description has been added."}
            </Typography>
          </Box>

          <Box
            sx={{
              display: "flex",
              flexWrap: "wrap",
              gap: 1,
            }}
          >
            <CapabilityStatusChip
              status={
                capability.approval_status
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
              Edit Capability
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
            label={`Type: ${capability.capability_type}`}
            sx={{
              bgcolor:
                "rgba(255,255,255,0.14)",
              color: "#ffffff",
              textTransform: "capitalize",
            }}
          />

          <Chip
            label={`Maturity: ${capability.maturity_level}`}
            sx={{
              bgcolor:
                "rgba(255,255,255,0.14)",
              color: "#ffffff",
              textTransform: "capitalize",
            }}
          />

          <Chip
            label={`Owner: ${
              capability.business_owner ||
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
            title="Capability Hierarchy"
          >
            <DetailLine
              label="Parent"
              value={
                parentCapability?.name ??
                "Top-level capability"
              }
            />

            <DetailLine
              label="Child capabilities"
              value={String(
                childCapabilities.length
              )}
            />

            {childCapabilities.map(
              (child) => (
                <Chip
                  key={child.id}
                  label={child.name}
                  size="small"
                  sx={{
                    mr: 0.8,
                    mt: 1,
                    bgcolor: "#fff3dc",
                    color: "#765019",
                  }}
                />
              )
            )}
          </InfoPanel>

          <InfoPanel
            title="Capability Confidence"
          >
            <Typography
              variant="h3"
              sx={{
                color: "#4f2c1a",
                fontWeight: 900,
              }}
            >
              {capability.confidence}%
            </Typography>

            <LinearProgress
              variant="determinate"
              value={capability.confidence}
              sx={{
                mt: 1.5,
                height: 9,
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
              Mapped Business Entities
            </Typography>

            <Typography
              variant="body2"
              sx={{ color: "#888888" }}
            >
              Business concepts that support or
              participate in this capability.
            </Typography>
          </Box>

          <Button
            variant="outlined"
            onClick={onMapEntity}
            sx={{
              textTransform: "none",
              fontWeight: 800,
              color: "#6b3b21",
              borderColor: "#9f795d",
            }}
          >
            Map Business Entity
          </Button>
        </Box>

        <Box
          sx={{
            mt: 2,
            display: "grid",
            gap: 1.3,
          }}
        >
          {capability.entity_mappings.length ===
          0 ? (
            <Alert severity="info">
              No business entities are mapped to
              this capability.
            </Alert>
          ) : (
            capability.entity_mappings.map(
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
                    alignItems: "center",
                    flexWrap: "wrap",
                    gap: 2,
                  }}
                >
                  <Box>
                    <Typography
                      sx={{
                        color: "#4f2c1a",
                        fontWeight: 800,
                      }}
                    >
                      {findEntityName(
                        mapping.business_entity_id
                      )}
                    </Typography>

                    <Typography
                      variant="caption"
                      sx={{
                        color: "#888888",
                      }}
                    >
                      {mapping.mapping_role} role ·{" "}
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
                      textTransform: "none",
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
              onClick={onToggleActive}
              sx={{
                textTransform: "none",
                fontWeight: 800,
                color: "#6b3b21",
                borderColor: "#9f795d",
              }}
            >
              {capability.is_active
                ? "Disable"
                : "Enable"}
            </Button>

            <Button
              variant="outlined"
              color="error"
              onClick={onDelete}
              sx={{
                textTransform: "none",
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
              Approve Capability
            </Button>
          </Box>
        </Box>
      </Box>
    </>
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
        sx={{ color: "#888888" }}
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


function CapabilityDialog({
  open,
  editing,
  form,
  capabilities,
  saving,
  onFormChange,
  onClose,
  onSave,
}: {
  open: boolean;
  editing: boolean;
  form: BusinessCapabilityCreate;
  capabilities: BusinessCapability[];
  saving: boolean;
  onFormChange: React.Dispatch<
    React.SetStateAction<BusinessCapabilityCreate>
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
      maxWidth="md"
    >
      <DialogTitle
        sx={{
          color: "#4f2c1a",
          fontWeight: 900,
        }}
      >
        {editing
          ? "Edit Business Capability"
          : "Create Business Capability"}
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
          <TextField
            label="Capability name"
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
          />

          <FormControl fullWidth>
            <InputLabel>
              Parent capability
            </InputLabel>

            <Select
              label="Parent capability"
              value={
                form.parent_capability_id ??
                ""
              }
              onChange={(event) =>
                onFormChange(
                  (current) => ({
                    ...current,
                    parent_capability_id:
                      event.target.value === ""
                        ? null
                        : Number(
                            event.target.value
                          ),
                  })
                )
              }
            >
              <MenuItem value="">
                Top-level capability
              </MenuItem>

              {capabilities.map(
                (capability) => (
                  <MenuItem
                    key={capability.id}
                    value={capability.id}
                  >
                    {capability.name}
                  </MenuItem>
                )
              )}
            </Select>
          </FormControl>

          <TextField
            label="Business owner"
            value={
              form.business_owner ?? ""
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

          <TextField
            label="Confidence"
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

          <FormControl fullWidth>
            <InputLabel>
              Capability type
            </InputLabel>

            <Select
              label="Capability type"
              value={
                form.capability_type
              }
              onChange={(event) =>
                onFormChange(
                  (current) => ({
                    ...current,
                    capability_type:
                      event.target
                        .value as CapabilityType,
                  })
                )
              }
            >
              <MenuItem value="strategic">
                Strategic
              </MenuItem>

              <MenuItem value="core">
                Core
              </MenuItem>

              <MenuItem value="operational">
                Operational
              </MenuItem>

              <MenuItem value="supporting">
                Supporting
              </MenuItem>

              <MenuItem value="control">
                Control
              </MenuItem>
            </Select>
          </FormControl>

          <FormControl fullWidth>
            <InputLabel>
              Maturity level
            </InputLabel>

            <Select
              label="Maturity level"
              value={
                form.maturity_level
              }
              onChange={(event) =>
                onFormChange(
                  (current) => ({
                    ...current,
                    maturity_level:
                      event.target
                        .value as CapabilityMaturityLevel,
                  })
                )
              }
            >
              <MenuItem value="initial">
                Initial
              </MenuItem>

              <MenuItem value="developing">
                Developing
              </MenuItem>

              <MenuItem value="defined">
                Defined
              </MenuItem>

              <MenuItem value="managed">
                Managed
              </MenuItem>

              <MenuItem value="optimized">
                Optimized
              </MenuItem>
            </Select>
          </FormControl>

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
            : "Save Capability"}
        </Button>
      </DialogActions>
    </Dialog>
  );
}


function EntityMappingDialog({
  open,
  entities,
  selectedEntityId,
  mappingRole,
  confidence,
  saving,
  onEntityChange,
  onRoleChange,
  onConfidenceChange,
  onClose,
  onSave,
}: {
  open: boolean;
  entities: BusinessEntity[];
  selectedEntityId: number | "";
  mappingRole: CapabilityEntityMappingRole;
  confidence: number;
  saving: boolean;
  onEntityChange:
    (value: number | "") => void;
  onRoleChange:
    (value: CapabilityEntityMappingRole) => void;
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
        Map Business Entity
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
              Business entity
            </InputLabel>

            <Select
              label="Business entity"
              value={selectedEntityId}
              onChange={(event) =>
                onEntityChange(
                  Number(
                    event.target.value
                  )
                )
              }
            >
              {entities.map((entity) => (
                <MenuItem
                  key={entity.id}
                  value={entity.id}
                >
                  {entity.name}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <FormControl fullWidth>
            <InputLabel>
              Mapping role
            </InputLabel>

            <Select
              label="Mapping role"
              value={mappingRole}
              onChange={(event) =>
                onRoleChange(
                  event.target
                    .value as CapabilityEntityMappingRole
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

              <MenuItem value="output">
                Output
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
            selectedEntityId === ""
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


function CapabilitySuggestionDialog({
  open,
  entities,
  selectedEntityIds,
  suggestion,
  generating,
  onEntitiesChange,
  onGenerate,
  onUse,
  onClose,
}: {
  open: boolean;
  entities: BusinessEntity[];
  selectedEntityIds: number[];
  suggestion:
    CapabilitySuggestion | null;
  generating: boolean;
  onEntitiesChange:
    (values: number[]) => void;
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
        Generate Capability Suggestion
      </DialogTitle>

      <DialogContent dividers>
        <FormControl fullWidth>
          <InputLabel>
            Business entities
          </InputLabel>

          <Select
            multiple
            label="Business entities"
            value={selectedEntityIds}
            onChange={(event) =>
              onEntitiesChange(
                typeof event.target.value ===
                  "string"
                  ? event.target.value
                      .split(",")
                      .map(Number)
                  : event.target.value
              )
            }
            renderValue={(selected) =>
              selected
                .map(
                  (entityId) =>
                    entities.find(
                      (entity) =>
                        entity.id === entityId
                    )?.name
                )
                .filter(Boolean)
                .join(", ")
            }
          >
            {entities.map((entity) => (
              <MenuItem
                key={entity.id}
                value={entity.id}
              >
                <Checkbox
                  checked={
                    selectedEntityIds.indexOf(
                      entity.id
                    ) > -1
                  }
                />

                <ListItemText
                  primary={entity.name}
                  secondary={
                    entity.approval_status
                  }
                />
              </MenuItem>
            ))}
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
              selectedEntityIds.length === 0
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
              variant="h4"
              sx={{
                color: "#4f2c1a",
                fontWeight: 900,
              }}
            >
              {suggestion.suggested_name}
            </Typography>

            <Typography
              sx={{
                mt: 1.5,
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
                gap: 1,
              }}
            >
              <Chip
                label={suggestion.capability_type}
                sx={{
                  textTransform:
                    "capitalize",
                }}
              />

              <Chip
                label={suggestion.maturity_level}
                sx={{
                  textTransform:
                    "capitalize",
                }}
              />

              <Chip
                label={`${suggestion.confidence}% confidence`}
                sx={{
                  bgcolor: "#e7f6ed",
                  color: "#207744",
                  fontWeight: 800,
                }}
              />
            </Box>

            <LinearProgress
              variant="determinate"
              value={suggestion.confidence}
              sx={{
                mt: 2,
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
          BC
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


function CapabilityStatusChip({
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


export default BusinessCapabilityRegistryPage;
