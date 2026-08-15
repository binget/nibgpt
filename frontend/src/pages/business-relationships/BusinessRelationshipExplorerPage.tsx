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
  createBusinessRelationship,
  deleteBusinessRelationship,
  getBusinessRelationships,
  suggestBusinessRelationship,
  updateBusinessRelationship,
} from "../../services/businessRelationships";

import {
  getBusinessDomains,
  getBusinessEntities,
} from "../../services/businessEntities";

import type {
  BusinessDomain,
  BusinessEntity,
} from "../../types/businessEntity";

import type {
  BusinessRelationship,
  BusinessRelationshipCreate,
  RelationshipApprovalStatus,
  RelationshipCardinality,
  RelationshipSuggestion,
  RelationshipType,
} from "../../types/businessRelationship";

function BusinessRelationshipExplorerPage() {
  const [domains, setDomains] =
    useState<BusinessDomain[]>([]);

  const [entities, setEntities] =
    useState<BusinessEntity[]>([]);

  const [relationships, setRelationships] =
    useState<BusinessRelationship[]>([]);

  const [selectedDomainId, setSelectedDomainId] =
    useState<number | "">("");

  const [selectedEntityId, setSelectedEntityId] =
    useState<number | "">("");

  const [approvalFilter, setApprovalFilter] =
    useState("");

  const [selectedRelationship, setSelectedRelationship] =
    useState<BusinessRelationship | null>(null);

  const [loading, setLoading] =
    useState(true);

  const [loadingRelationships, setLoadingRelationships] =
    useState(false);

  const [relationshipDialogOpen, setRelationshipDialogOpen] =
    useState(false);

  const [suggestionDialogOpen, setSuggestionDialogOpen] =
    useState(false);

  const [savingRelationship, setSavingRelationship] =
    useState(false);

  const [generatingSuggestion, setGeneratingSuggestion] =
    useState(false);

  const [editingRelationship, setEditingRelationship] =
    useState<BusinessRelationship | null>(null);

  const [suggestion, setSuggestion] =
    useState<RelationshipSuggestion | null>(null);

  const [suggestionSourceId, setSuggestionSourceId] =
    useState<number | "">("");

  const [suggestionTargetId, setSuggestionTargetId] =
    useState<number | "">("");

  const [message, setMessage] =
    useState("");

  const [messageType, setMessageType] =
    useState<"success" | "error">("success");

  const [relationshipForm, setRelationshipForm] =
    useState<BusinessRelationshipCreate>({
      source_entity_id: 0,
      target_entity_id: 0,
      relationship_name: "",
      inverse_relationship_name: "",
      relationship_type: "business",
      cardinality: "many_to_one",
      description: "",
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
        relationshipResult,
      ] = await Promise.all([
        getBusinessDomains(),
        getBusinessEntities(),
        getBusinessRelationships(),
      ]);

      setDomains(domainResult);
      setEntities(entityResult);
      setRelationships(relationshipResult);

      if (domainResult.length > 0) {
        setSelectedDomainId(domainResult[0].id);
      }
    } catch (error: any) {
      showMessage(
        error?.response?.data?.detail ??
          "Unable to load the Relationship Explorer.",
        "error"
      );
    } finally {
      setLoading(false);
    }
  };

  const loadRelationships = async () => {
    try {
      setLoadingRelationships(true);

      const result = await getBusinessRelationships(
        selectedEntityId === ""
          ? undefined
          : selectedEntityId,
        approvalFilter || undefined
      );

      setRelationships(result);
      setSelectedRelationship(null);
    } catch (error: any) {
      showMessage(
        error?.response?.data?.detail ??
          "Unable to load business relationships.",
        "error"
      );
    } finally {
      setLoadingRelationships(false);
    }
  };

  useEffect(() => {
    loadInitialData();
  }, []);

  useEffect(() => {
    if (!loading) {
      loadRelationships();
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
        entity.domain_id === selectedDomainId
    );
  }, [
    entities,
    selectedDomainId,
  ]);

  const approvedRelationships = useMemo(
    () =>
      relationships.filter(
        (relationship) =>
          relationship.approval_status ===
          "approved"
      ).length,
    [relationships]
  );

  const pendingRelationships = useMemo(
    () =>
      relationships.filter(
        (relationship) =>
          relationship.approval_status ===
            "draft" ||
          relationship.approval_status ===
            "generated"
      ).length,
    [relationships]
  );

  const averageConfidence = useMemo(() => {
    if (!relationships.length) {
      return 0;
    }

    return Math.round(
      relationships.reduce(
        (total, relationship) =>
          total + relationship.confidence,
        0
      ) / relationships.length
    );
  }, [relationships]);

  const openCreateRelationship = () => {
    setEditingRelationship(null);

    setRelationshipForm({
      source_entity_id:
        selectedEntityId === ""
          ? 0
          : selectedEntityId,
      target_entity_id: 0,
      relationship_name: "",
      inverse_relationship_name: "",
      relationship_type: "business",
      cardinality: "many_to_one",
      description: "",
      confidence: 0,
    });

    setRelationshipDialogOpen(true);
  };

  const openEditRelationship = (
    relationship: BusinessRelationship
  ) => {
    setEditingRelationship(relationship);

    setRelationshipForm({
      source_entity_id:
        relationship.source_entity_id,
      target_entity_id:
        relationship.target_entity_id,
      relationship_name:
        relationship.relationship_name,
      inverse_relationship_name:
        relationship.inverse_relationship_name ??
        "",
      relationship_type:
        relationship.relationship_type,
      cardinality:
        relationship.cardinality,
      description:
        relationship.description ?? "",
      confidence:
        relationship.confidence,
    });

    setRelationshipDialogOpen(true);
  };

  const saveRelationship = async () => {
    if (
      !relationshipForm.source_entity_id ||
      !relationshipForm.target_entity_id
    ) {
      showMessage(
        "Source and target entities are required.",
        "error"
      );
      return;
    }

    if (
      relationshipForm.source_entity_id ===
      relationshipForm.target_entity_id
    ) {
      showMessage(
        "Source and target entities must be different.",
        "error"
      );
      return;
    }

    if (
      !relationshipForm.relationship_name.trim()
    ) {
      showMessage(
        "Relationship name is required.",
        "error"
      );
      return;
    }

    try {
      setSavingRelationship(true);

      if (editingRelationship) {
        const updated =
          await updateBusinessRelationship(
            editingRelationship.id,
            {
              relationship_name:
                relationshipForm.relationship_name.trim(),
              inverse_relationship_name:
                relationshipForm
                  .inverse_relationship_name
                  ?.trim() || null,
              relationship_type:
                relationshipForm.relationship_type,
              cardinality:
                relationshipForm.cardinality,
              description:
                relationshipForm.description?.trim() ||
                null,
              confidence:
                relationshipForm.confidence,
            }
          );

        setRelationships((current) =>
          current.map((item) =>
            item.id === updated.id
              ? updated
              : item
          )
        );

        setSelectedRelationship(updated);

        showMessage(
          "Business relationship updated successfully.",
          "success"
        );
      } else {
        const created =
          await createBusinessRelationship({
            ...relationshipForm,
            relationship_name:
              relationshipForm.relationship_name.trim(),
            inverse_relationship_name:
              relationshipForm
                .inverse_relationship_name
                ?.trim() || null,
            description:
              relationshipForm.description?.trim() ||
              null,
          });

        setRelationships((current) => [
          ...current,
          created,
        ]);

        setSelectedRelationship(created);

        showMessage(
          "Business relationship created successfully.",
          "success"
        );
      }

      setRelationshipDialogOpen(false);
    } catch (error: any) {
      showMessage(
        error?.response?.data?.detail ??
          "Unable to save business relationship.",
        "error"
      );
    } finally {
      setSavingRelationship(false);
    }
  };

  const updateApproval = async (
    relationship: BusinessRelationship,
    approvalStatus: RelationshipApprovalStatus
  ) => {
    try {
      const updated =
        await updateBusinessRelationship(
          relationship.id,
          {
            approval_status:
              approvalStatus,
          }
        );

      setRelationships((current) =>
        current.map((item) =>
          item.id === updated.id
            ? updated
            : item
        )
      );

      if (
        selectedRelationship?.id ===
        updated.id
      ) {
        setSelectedRelationship(updated);
      }

      showMessage(
        approvalStatus === "approved"
          ? "Business relationship approved."
          : approvalStatus === "rejected"
            ? "Business relationship rejected."
            : "Relationship status updated.",
        approvalStatus === "rejected"
          ? "error"
          : "success"
      );
    } catch (error: any) {
      showMessage(
        error?.response?.data?.detail ??
          "Unable to update relationship approval.",
        "error"
      );
    }
  };

  const toggleRelationshipActive = async (
    relationship: BusinessRelationship
  ) => {
    try {
      const updated =
        await updateBusinessRelationship(
          relationship.id,
          {
            is_active:
              !relationship.is_active,
          }
        );

      setRelationships((current) =>
        current.map((item) =>
          item.id === updated.id
            ? updated
            : item
        )
      );

      setSelectedRelationship(updated);

      showMessage(
        updated.is_active
          ? "Relationship enabled."
          : "Relationship disabled.",
        "success"
      );
    } catch (error: any) {
      showMessage(
        error?.response?.data?.detail ??
          "Unable to update relationship status.",
        "error"
      );
    }
  };

  const removeRelationship = async (
    relationshipId: number
  ) => {
    const confirmed = window.confirm(
      "Delete this business relationship?"
    );

    if (!confirmed) {
      return;
    }

    try {
      await deleteBusinessRelationship(
        relationshipId
      );

      setRelationships((current) =>
        current.filter(
          (relationship) =>
            relationship.id !==
            relationshipId
        )
      );

      setSelectedRelationship(null);

      showMessage(
        "Business relationship deleted.",
        "success"
      );
    } catch (error: any) {
      showMessage(
        error?.response?.data?.detail ??
          "Unable to delete business relationship.",
        "error"
      );
    }
  };

  const openSuggestionDialog = () => {
    setSuggestion(null);

    setSuggestionSourceId(
      selectedEntityId === ""
        ? ""
        : selectedEntityId
    );

    setSuggestionTargetId("");
    setSuggestionDialogOpen(true);
  };

  const generateSuggestion = async () => {
    if (
      suggestionSourceId === "" ||
      suggestionTargetId === ""
    ) {
      showMessage(
        "Select both source and target entities.",
        "error"
      );
      return;
    }

    if (
      suggestionSourceId ===
      suggestionTargetId
    ) {
      showMessage(
        "Source and target entities must be different.",
        "error"
      );
      return;
    }

    try {
      setGeneratingSuggestion(true);

      const result =
        await suggestBusinessRelationship(
          suggestionSourceId,
          suggestionTargetId
        );

      setSuggestion(result);
    } catch (error: any) {
      showMessage(
        error?.response?.data?.detail ??
          "Unable to generate relationship suggestion.",
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

    setEditingRelationship(null);

    setRelationshipForm({
      source_entity_id:
        suggestion.source_entity_id,
      target_entity_id:
        suggestion.target_entity_id,
      relationship_name:
        suggestion.relationship_name,
      inverse_relationship_name:
        suggestion.inverse_relationship_name ??
        "",
      relationship_type:
        suggestion.relationship_type,
      cardinality:
        suggestion.cardinality,
      description:
        suggestion.description,
      confidence:
        suggestion.confidence,
    });

    setSuggestionDialogOpen(false);
    setRelationshipDialogOpen(true);
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
            Loading business relationships...
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
            Relationship Explorer
          </Typography>

          <Typography
            sx={{
              mt: 0.7,
              color: "#777777",
            }}
          >
            Define and govern how business
            concepts connect across NIBGPT.
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
            onClick={openCreateRelationship}
            sx={{
              textTransform: "none",
              fontWeight: 800,
              background:
                "linear-gradient(90deg, #61351f, #c78f2b)",
            }}
          >
            New Relationship
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
          label="Approved Relationships"
          value={String(
            approvedRelationships
          )}
          description="Trusted connections available to NIBGPT"
        />

        <SummaryCard
          label="Pending Review"
          value={String(
            pendingRelationships
          )}
          description="Generated or draft connections awaiting review"
        />

        <SummaryCard
          label="Average Confidence"
          value={`${averageConfidence}%`}
          description="Semantic confidence across displayed relationships"
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
              md: "repeat(3, minmax(0, 1fr))",
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
                const value = Number(
                  event.target.value
                );

                setSelectedDomainId(value);
                setSelectedEntityId("");
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
              value={selectedEntityId}
              onChange={(event) =>
                setSelectedEntityId(
                  event.target.value === ""
                    ? ""
                    : Number(
                        event.target.value
                      )
                )
              }
            >
              <MenuItem value="">
                All entities in registry
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
              Business Connections
            </Typography>

            <Typography
              variant="body2"
              sx={{
                color: "#888888",
              }}
            >
              Select a relationship to review
              its semantic meaning.
            </Typography>
          </Box>

          <Box
            sx={{
              p: 1.5,
              maxHeight: 740,
              overflowY: "auto",
            }}
          >
            {loadingRelationships ? (
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
            ) : relationships.length === 0 ? (
              <EmptyState
                title="No relationships found"
                description="Create a relationship manually or generate a suggestion between two approved entities."
              />
            ) : (
              relationships.map(
                (relationship) => (
                  <RelationshipListItem
                    key={relationship.id}
                    relationship={
                      relationship
                    }
                    selected={
                      selectedRelationship?.id ===
                      relationship.id
                    }
                    onClick={() =>
                      setSelectedRelationship(
                        relationship
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
          {!selectedRelationship ? (
            <EmptyState
              title="Select a relationship"
              description="Choose a relationship to inspect its direction, type, cardinality, confidence and approval status."
            />
          ) : (
            <RelationshipDetails
              relationship={
                selectedRelationship
              }
              onEdit={() =>
                openEditRelationship(
                  selectedRelationship
                )
              }
              onApprove={() =>
                updateApproval(
                  selectedRelationship,
                  "approved"
                )
              }
              onReject={() =>
                updateApproval(
                  selectedRelationship,
                  "rejected"
                )
              }
              onToggleActive={() =>
                toggleRelationshipActive(
                  selectedRelationship
                )
              }
              onDelete={() =>
                removeRelationship(
                  selectedRelationship.id
                )
              }
            />
          )}
        </Paper>
      </Box>

      <RelationshipDialog
        open={relationshipDialogOpen}
        editing={Boolean(
          editingRelationship
        )}
        entities={entities}
        form={relationshipForm}
        saving={savingRelationship}
        onFormChange={
          setRelationshipForm
        }
        onClose={() =>
          setRelationshipDialogOpen(
            false
          )
        }
        onSave={saveRelationship}
      />

      <SuggestionDialog
        open={suggestionDialogOpen}
        entities={entities}
        sourceEntityId={
          suggestionSourceId
        }
        targetEntityId={
          suggestionTargetId
        }
        suggestion={suggestion}
        generating={
          generatingSuggestion
        }
        onSourceChange={
          setSuggestionSourceId
        }
        onTargetChange={
          setSuggestionTargetId
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

function RelationshipListItem({
  relationship,
  selected,
  onClick,
}: {
  relationship: BusinessRelationship;
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
            {
              relationship
                .source_entity.name
            }
          </Typography>

          <Typography
            variant="body2"
            sx={{
              my: 0.5,
              color: "#a06b1f",
              fontWeight: 800,
            }}
          >
            {
              relationship.relationship_name
            }
          </Typography>

          <Typography
            sx={{
              color: "#4f2c1a",
              fontWeight: 900,
            }}
          >
            {
              relationship
                .target_entity.name
            }
          </Typography>
        </Box>

        <RelationshipStatusChip
          status={
            relationship.approval_status
          }
        />
      </Box>

      <LinearProgress
        variant="determinate"
        value={
          relationship.confidence
        }
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
        {relationship.confidence}%
        confidence ·{" "}
        {relationship.cardinality.replaceAll(
          "_",
          " "
        )}
      </Typography>
    </Box>
  );
}

function RelationshipDetails({
  relationship,
  onEdit,
  onApprove,
  onReject,
  onToggleActive,
  onDelete,
}: {
  relationship: BusinessRelationship;
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
            alignItems: "flex-start",
            flexWrap: "wrap",
            gap: 2,
          }}
        >
          <Box>
            <Typography
              variant="h5"
              sx={{ fontWeight: 900 }}
            >
              {
                relationship
                  .source_entity.name
              }
            </Typography>

            <Typography
              variant="h6"
              sx={{
                my: 1,
                color: "#ffdca0",
                fontWeight: 900,
              }}
            >
              {
                relationship.relationship_name
              }
            </Typography>

            <Typography
              variant="h5"
              sx={{ fontWeight: 900 }}
            >
              {
                relationship
                  .target_entity.name
              }
            </Typography>
          </Box>

          <Box
            sx={{
              display: "flex",
              flexWrap: "wrap",
              gap: 1,
            }}
          >
            <RelationshipStatusChip
              status={
                relationship.approval_status
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
              Edit Relationship
            </Button>
          </Box>
        </Box>

        <Typography
          sx={{
            mt: 2,
            maxWidth: 720,
            color:
              "rgba(255,255,255,0.78)",
            lineHeight: 1.7,
          }}
        >
          {relationship.description ||
            "No business relationship description has been added."}
        </Typography>
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
          <InfoPanel title="Relationship Direction">
            <Typography
              sx={{
                color: "#4f2c1a",
                fontWeight: 900,
              }}
            >
              {
                relationship
                  .source_entity.name
              }{" "}
              →{" "}
              {
                relationship.relationship_name
              }{" "}
              →{" "}
              {
                relationship
                  .target_entity.name
              }
            </Typography>

            {relationship.inverse_relationship_name && (
              <Typography
                variant="body2"
                sx={{
                  mt: 1,
                  color: "#777777",
                }}
              >
                Inverse:{" "}
                {
                  relationship
                    .target_entity.name
                }{" "}
                →{" "}
                {
                  relationship.inverse_relationship_name
                }{" "}
                →{" "}
                {
                  relationship
                    .source_entity.name
                }
              </Typography>
            )}
          </InfoPanel>

          <InfoPanel title="Relationship Governance">
            <DetailLine
              label="Type"
              value={relationship.relationship_type.replaceAll(
                "_",
                " "
              )}
            />

            <DetailLine
              label="Cardinality"
              value={relationship.cardinality.replaceAll(
                "_",
                " "
              )}
            />

            <DetailLine
              label="Status"
              value={relationship.is_active
                ? "Active"
                : "Disabled"}
            />
          </InfoPanel>

          <InfoPanel title="Semantic Confidence">
            <Typography
              variant="h3"
              sx={{
                color: "#4f2c1a",
                fontWeight: 900,
              }}
            >
              {relationship.confidence}%
            </Typography>

            <LinearProgress
              variant="determinate"
              value={
                relationship.confidence
              }
              sx={{
                mt: 1.5,
                height: 9,
                borderRadius: 5,
              }}
            />
          </InfoPanel>

          <InfoPanel title="Approval State">
            <RelationshipStatusChip
              status={
                relationship.approval_status
              }
            />

            <Typography
              variant="body2"
              sx={{
                mt: 1.5,
                color: "#777777",
                lineHeight: 1.6,
              }}
            >
              Only approved and active
              relationships should be used by
              the future reasoning engine.
            </Typography>
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
              flexWrap: "wrap",
              gap: 1,
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
              {relationship.is_active
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
              Approve Relationship
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
          textTransform: "capitalize",
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

function RelationshipDialog({
  open,
  editing,
  entities,
  form,
  saving,
  onFormChange,
  onClose,
  onSave,
}: {
  open: boolean;
  editing: boolean;
  entities: BusinessEntity[];
  form: BusinessRelationshipCreate;
  saving: boolean;
  onFormChange: React.Dispatch<
    React.SetStateAction<BusinessRelationshipCreate>
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
          ? "Edit Business Relationship"
          : "Create Business Relationship"}
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
          <FormControl
            fullWidth
            disabled={editing}
          >
            <InputLabel>
              Source entity
            </InputLabel>

            <Select
              label="Source entity"
              value={
                form.source_entity_id ||
                ""
              }
              onChange={(event) =>
                onFormChange(
                  (current) => ({
                    ...current,
                    source_entity_id:
                      Number(
                        event.target.value
                      ),
                  })
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

          <FormControl
            fullWidth
            disabled={editing}
          >
            <InputLabel>
              Target entity
            </InputLabel>

            <Select
              label="Target entity"
              value={
                form.target_entity_id ||
                ""
              }
              onChange={(event) =>
                onFormChange(
                  (current) => ({
                    ...current,
                    target_entity_id:
                      Number(
                        event.target.value
                      ),
                  })
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

          <TextField
            label="Relationship name"
            value={
              form.relationship_name
            }
            onChange={(event) =>
              onFormChange(
                (current) => ({
                  ...current,
                  relationship_name:
                    event.target.value,
                })
              )
            }
            placeholder="Example: owns"
          />

          <TextField
            label="Inverse relationship"
            value={
              form.inverse_relationship_name ??
              ""
            }
            onChange={(event) =>
              onFormChange(
                (current) => ({
                  ...current,
                  inverse_relationship_name:
                    event.target.value,
                })
              )
            }
            placeholder="Example: belongs to"
          />

          <FormControl fullWidth>
            <InputLabel>
              Relationship type
            </InputLabel>

            <Select
              label="Relationship type"
              value={
                form.relationship_type
              }
              onChange={(event) =>
                onFormChange(
                  (current) => ({
                    ...current,
                    relationship_type:
                      event.target
                        .value as RelationshipType,
                  })
                )
              }
            >
              <MenuItem value="business">
                Business
              </MenuItem>

              <MenuItem value="reference">
                Reference
              </MenuItem>

              <MenuItem value="dependency">
                Dependency
              </MenuItem>

              <MenuItem value="hierarchical">
                Hierarchical
              </MenuItem>

              <MenuItem value="process">
                Process
              </MenuItem>
            </Select>
          </FormControl>

          <FormControl fullWidth>
            <InputLabel>
              Cardinality
            </InputLabel>

            <Select
              label="Cardinality"
              value={form.cardinality}
              onChange={(event) =>
                onFormChange(
                  (current) => ({
                    ...current,
                    cardinality:
                      event.target
                        .value as RelationshipCardinality,
                  })
                )
              }
            >
              <MenuItem value="one_to_one">
                One to One
              </MenuItem>

              <MenuItem value="one_to_many">
                One to Many
              </MenuItem>

              <MenuItem value="many_to_one">
                Many to One
              </MenuItem>

              <MenuItem value="many_to_many">
                Many to Many
              </MenuItem>
            </Select>
          </FormControl>

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
            : "Save Relationship"}
        </Button>
      </DialogActions>
    </Dialog>
  );
}

function SuggestionDialog({
  open,
  entities,
  sourceEntityId,
  targetEntityId,
  suggestion,
  generating,
  onSourceChange,
  onTargetChange,
  onGenerate,
  onUse,
  onClose,
}: {
  open: boolean;
  entities: BusinessEntity[];
  sourceEntityId: number | "";
  targetEntityId: number | "";
  suggestion:
    RelationshipSuggestion | null;
  generating: boolean;
  onSourceChange:
    (value: number | "") => void;
  onTargetChange:
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
        Generate Relationship Suggestion
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
              Source entity
            </InputLabel>

            <Select
              label="Source entity"
              value={sourceEntityId}
              onChange={(event) =>
                onSourceChange(
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
              Target entity
            </InputLabel>

            <Select
              label="Target entity"
              value={targetEntityId}
              onChange={(event) =>
                onTargetChange(
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
        </Box>

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
              sourceEntityId === "" ||
              targetEntityId === ""
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
                Analysing relationship...
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
              variant="h5"
              sx={{
                color: "#4f2c1a",
                fontWeight: 900,
              }}
            >
              {
                suggestion.relationship_name
              }
            </Typography>

            {suggestion.inverse_relationship_name && (
              <Typography
                variant="body2"
                sx={{
                  mt: 0.6,
                  color: "#888888",
                }}
              >
                Inverse relationship:{" "}
                {
                  suggestion.inverse_relationship_name
                }
              </Typography>
            )}

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
                gap: 1,
              }}
            >
              <Chip
                label={suggestion.relationship_type}
                sx={{
                  textTransform:
                    "capitalize",
                }}
              />

              <Chip
                label={suggestion.cardinality.replaceAll(
                  "_",
                  " "
                )}
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
              value={
                suggestion.confidence
              }
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
          RE
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

function RelationshipStatusChip({
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

export default BusinessRelationshipExplorerPage;
