import {
  Alert,
  Box,
  Chip,
  CircularProgress,
  FormControl,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Typography,
} from "@mui/material";

import {
  Background,
  Controls,
  MarkerType,
  MiniMap,
  ReactFlow,
  type Edge,
  type Node,
} from "@xyflow/react";

import "@xyflow/react/dist/style.css";

import {
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  getBusinessDomains,
  getBusinessEntities,
} from "../../services/businessEntities";

import {
  getBusinessRelationships,
} from "../../services/businessRelationships";

import type {
  BusinessDomain,
  BusinessEntity,
} from "../../types/businessEntity";

import type {
  BusinessRelationship,
} from "../../types/businessRelationship";


function KnowledgeGraphPage() {
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

  const [loading, setLoading] =
    useState(true);

  const [errorMessage, setErrorMessage] =
    useState("");


  useEffect(() => {
    const loadGraphData = async () => {
      try {
        setLoading(true);

        const [
          domainResult,
          entityResult,
          relationshipResult,
        ] = await Promise.all([
          getBusinessDomains(),
          getBusinessEntities(),
          getBusinessRelationships(
            undefined,
            "approved"
          ),
        ]);

        const approvedEntities =
          entityResult.filter(
            (entity) =>
              entity.approval_status ===
                "approved" &&
              entity.is_active
          );

        const approvedRelationships =
          relationshipResult.filter(
            (relationship) =>
              relationship.approval_status ===
                "approved" &&
              relationship.is_active
          );

        setDomains(
          domainResult.filter(
            (domain) => domain.is_active
          )
        );

        setEntities(approvedEntities);
        setRelationships(
          approvedRelationships
        );
      } catch (error: any) {
        setErrorMessage(
          error?.response?.data?.detail ??
            "Unable to load the enterprise knowledge graph."
        );
      } finally {
        setLoading(false);
      }
    };

    loadGraphData();
  }, []);


  const visibleEntities = useMemo(() => {
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


  const visibleEntityIds = useMemo(
    () =>
      new Set(
        visibleEntities.map(
          (entity) => entity.id
        )
      ),
    [visibleEntities]
  );


  const visibleRelationships =
    useMemo(() => {
      return relationships.filter(
        (relationship) =>
          visibleEntityIds.has(
            relationship.source_entity_id
          ) &&
          visibleEntityIds.has(
            relationship.target_entity_id
          )
      );
    }, [
      relationships,
      visibleEntityIds,
    ]);


  const graphNodes = useMemo<Node[]>(() => {
    const domainGroups =
      new Map<number, BusinessEntity[]>();

    for (const entity of visibleEntities) {
      const group =
        domainGroups.get(
          entity.domain_id
        ) ?? [];

      group.push(entity);

      domainGroups.set(
        entity.domain_id,
        group
      );
    }

    const nodes: Node[] = [];

    let domainIndex = 0;

    for (const [
      domainId,
      domainEntities,
    ] of domainGroups.entries()) {
      const column =
        domainIndex % 3;

      const row =
        Math.floor(domainIndex / 3);

      const baseX =
        column * 620;

      const baseY =
        row * 520;

      domainEntities.forEach(
        (entity, entityIndex) => {
          const angle =
            (
              entityIndex /
              Math.max(
                domainEntities.length,
                1
              )
            ) *
            Math.PI *
            2;

          const radius =
            domainEntities.length === 1
              ? 0
              : 170;

          const x =
            baseX +
            260 +
            Math.cos(angle) * radius;

          const y =
            baseY +
            220 +
            Math.sin(angle) * radius;

          nodes.push({
            id: String(entity.id),
            position: {
              x,
              y,
            },
            data: {
              label: entity.name,
              entity,
            },
            type: "default",
            style: {
              width: 190,
              padding: 14,
              borderRadius: 16,
              border:
                selectedEntityId ===
                entity.id
                  ? "2px solid #d39c32"
                  : "1px solid #cfb995",
              background:
                selectedEntityId ===
                entity.id
                  ? "#fff3dc"
                  : "#ffffff",
              color: "#4f2c1a",
              fontWeight: 800,
              boxShadow:
                "0 10px 24px rgba(81, 45, 24, 0.10)",
            },
          });
        }
      );

      domainIndex += 1;
    }

    return nodes;
  }, [
    visibleEntities,
    selectedEntityId,
  ]);


  const graphEdges = useMemo<Edge[]>(
    () =>
      visibleRelationships.map(
        (relationship) => ({
          id: String(
            relationship.id
          ),
          source: String(
            relationship.source_entity_id
          ),
          target: String(
            relationship.target_entity_id
          ),
          label:
            relationship.relationship_name,
          animated:
            relationship.confidence >= 90,
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: "#9a672c",
          },
          style: {
            stroke: "#9a672c",
            strokeWidth: 2,
          },
          labelStyle: {
            fill: "#6b3b21",
            fontWeight: 700,
          },
          labelBgStyle: {
            fill: "#fffaf2",
            fillOpacity: 0.96,
          },
        })
      ),
    [visibleRelationships]
  );


  const selectedEntity =
    entities.find(
      (entity) =>
        entity.id === selectedEntityId
    ) ?? null;


  const connectedRelationships =
    useMemo(() => {
      if (selectedEntityId === "") {
        return [];
      }

      return relationships.filter(
        (relationship) =>
          relationship.source_entity_id ===
            selectedEntityId ||
          relationship.target_entity_id ===
            selectedEntityId
      );
    }, [
      relationships,
      selectedEntityId,
    ]);


  if (loading) {
    return (
      <Box
        sx={{
          minHeight: 520,
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
            Building the enterprise knowledge graph...
          </Typography>
        </Box>
      </Box>
    );
  }


  if (errorMessage) {
    return (
      <Alert severity="error">
        {errorMessage}
      </Alert>
    );
  }


  return (
    <Box>
      <Box sx={{ mb: 3 }}>
        <Typography
          variant="h4"
          sx={{
            color: "#4f2c1a",
            fontWeight: 900,
          }}
        >
          Enterprise Knowledge Graph
        </Typography>

        <Typography
          sx={{
            mt: 0.7,
            color: "#777777",
          }}
        >
          Explore approved business entities and
          their governed semantic relationships.
        </Typography>
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
              onChange={(event) => {
                const value =
                  event.target.value;

                setSelectedDomainId(
                  value === ""
                    ? ""
                    : Number(value)
                );

                setSelectedEntityId("");
              }}
            >
              <MenuItem value="">
                All approved domains
              </MenuItem>

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
              Focus entity
            </InputLabel>

            <Select
              label="Focus entity"
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
                Show complete graph
              </MenuItem>

              {visibleEntities.map(
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
        </Box>
      </Paper>

      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: {
            xs: "1fr",
            xl: "minmax(0, 1.7fr) 360px",
          },
          gap: 2.5,
        }}
      >
        <Paper
          elevation={0}
          sx={{
            height: 720,
            overflow: "hidden",
            borderRadius: 3,
            border: "1px solid #e9e2da",
            bgcolor: "#fbfaf8",
          }}
        >
          {graphNodes.length === 0 ? (
            <Box
              sx={{
                height: "100%",
                display: "grid",
                placeItems: "center",
                p: 4,
                textAlign: "center",
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
                  No approved graph data
                </Typography>

                <Typography
                  variant="body2"
                  sx={{
                    mt: 1,
                    color: "#888888",
                  }}
                >
                  Approve business entities and
                  relationships to display them here.
                </Typography>
              </Box>
            </Box>
          ) : (
            <ReactFlow
              nodes={graphNodes}
              edges={graphEdges}
              fitView
              minZoom={0.25}
              maxZoom={1.8}
              onNodeClick={(
                _event,
                node
              ) =>
                setSelectedEntityId(
                  Number(node.id)
                )
              }
            >
              <Background
                color="#e8dfd5"
                gap={24}
              />

              <MiniMap
                nodeColor={(node) =>
                  Number(node.id) ===
                  selectedEntityId
                    ? "#d39c32"
                    : "#7d4924"
                }
                maskColor="rgba(250,248,245,0.78)"
              />

              <Controls />
            </ReactFlow>
          )}
        </Paper>

        <Paper
          elevation={0}
          sx={{
            p: 3,
            minHeight: 720,
            borderRadius: 3,
            border: "1px solid #e9e2da",
          }}
        >
          {!selectedEntity ? (
            <Box
              sx={{
                minHeight: 600,
                display: "grid",
                placeItems: "center",
                textAlign: "center",
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
                  Select a business entity
                </Typography>

                <Typography
                  variant="body2"
                  sx={{
                    mt: 1,
                    color: "#888888",
                  }}
                >
                  Click a graph node to inspect its
                  business meaning and relationships.
                </Typography>
              </Box>
            </Box>
          ) : (
            <>
              <Typography
                variant="h5"
                sx={{
                  color: "#4f2c1a",
                  fontWeight: 900,
                }}
              >
                {selectedEntity.name}
              </Typography>

              <Typography
                variant="body2"
                sx={{
                  mt: 1,
                  color: "#777777",
                  lineHeight: 1.7,
                }}
              >
                {selectedEntity.description ||
                  "No approved description is available."}
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
                  label={
                    selectedEntity.classification
                  }
                  sx={{
                    textTransform:
                      "capitalize",
                  }}
                />

                <Chip
                  label={`${selectedEntity.confidence}% confidence`}
                  sx={{
                    bgcolor: "#e7f6ed",
                    color: "#207744",
                    fontWeight: 800,
                  }}
                />

                <Chip
                  label={`${selectedEntity.table_mappings.length} physical mapping(s)`}
                  sx={{
                    bgcolor: "#fff3dc",
                    color: "#765019",
                  }}
                />
              </Box>

              <Typography
                sx={{
                  mt: 3,
                  mb: 1.5,
                  color: "#4f2c1a",
                  fontWeight: 900,
                }}
              >
                Connected Business Concepts
              </Typography>

              {connectedRelationships.length ===
              0 ? (
                <Alert severity="info">
                  This entity has no approved
                  relationships.
                </Alert>
              ) : (
                <Box
                  sx={{
                    display: "grid",
                    gap: 1.2,
                  }}
                >
                  {connectedRelationships.map(
                    (relationship) => {
                      const outgoing =
                        relationship.source_entity_id ===
                        selectedEntity.id;

                      const relatedEntity =
                        outgoing
                          ? relationship.target_entity
                          : relationship.source_entity;

                      const relationLabel =
                        outgoing
                          ? relationship.relationship_name
                          : relationship.inverse_relationship_name ||
                            relationship.relationship_name;

                      return (
                        <Paper
                          key={
                            relationship.id
                          }
                          elevation={0}
                          sx={{
                            p: 1.8,
                            borderRadius: 2.5,
                            bgcolor: "#faf8f5",
                            border:
                              "1px solid #ece5dd",
                            cursor: "pointer",
                          }}
                          onClick={() =>
                            setSelectedEntityId(
                              relatedEntity.id
                            )
                          }
                        >
                          <Typography
                            variant="caption"
                            sx={{
                              color: "#9a672c",
                              fontWeight: 800,
                            }}
                          >
                            {relationLabel}
                          </Typography>

                          <Typography
                            sx={{
                              mt: 0.4,
                              color: "#4f2c1a",
                              fontWeight: 900,
                            }}
                          >
                            {relatedEntity.name}
                          </Typography>

                          <Typography
                            variant="caption"
                            sx={{
                              color: "#888888",
                            }}
                          >
                            {
                              relationship.cardinality
                            }{" "}
                            ·{" "}
                            {
                              relationship.confidence
                            }
                            % confidence
                          </Typography>
                        </Paper>
                      );
                    }
                  )}
                </Box>
              )}
            </>
          )}
        </Paper>
      </Box>
    </Box>
  );
}

export default KnowledgeGraphPage;
