import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Divider,
  FormControl,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Snackbar,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
  Checkbox,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControlLabel,
  Switch,
} from "@mui/material";

import {
  useEffect,
  useMemo,
  useState,
} from "react";

import { getDataSources } from "../../services/dataSources";


import GenerateDefinitionDialog from "../../components/metadata/GenerateDefinitionDialog";

import {
  applyGeneratedDefinition,
  approveGeneratedDefinition,
  generateTableDefinition,
  getMetadataTable,
  getMetadataTables,
  scanMetadata,
  updateMetadataColumn,
  updateMetadataTable,
} from "../../services/metadata";

import type { DataSource } from "../../types/dataSource";

import type {
  DataClassification,
  GeneratedTableDefinition,
  MetadataColumn,
  MetadataColumnUpdate,
  MetadataTableDetail,
  MetadataTableSummary,
  MetadataTableUpdate,
} from "../../types/metadata";




function MetadataExplorerPage() {
  const [dataSources, setDataSources] = useState<DataSource[]>([]);
  const [tables, setTables] = useState<MetadataTableSummary[]>([]);
  const [selectedTable, setSelectedTable] =
    useState<MetadataTableDetail | null>(null);

  const [selectedSourceId, setSelectedSourceId] =
    useState<number | "">("");

  const [search, setSearch] = useState("");

  const [loadingSources, setLoadingSources] = useState(true);
  const [loadingTables, setLoadingTables] = useState(false);
  const [loadingTable, setLoadingTable] = useState(false);
  const [scanning, setScanning] = useState(false);

  const [generatorOpen, setGeneratorOpen] =
  useState(false);

const [generatedPreview, setGeneratedPreview] =
  useState<GeneratedTableDefinition | null>(null);

const [generatingDefinition, setGeneratingDefinition] =
  useState(false);

const [applyingDefinition, setApplyingDefinition] =
  useState(false);

const [approvingDefinition, setApprovingDefinition] =
  useState(false);

  const [message, setMessage] = useState("");
  const [messageType, setMessageType] =
    useState<"success" | "error">("success");

    const [tableEditorOpen, setTableEditorOpen] =
  useState(false);

const [columnEditorOpen, setColumnEditorOpen] =
  useState(false);

const [editingColumn, setEditingColumn] =
  useState<MetadataColumn | null>(null);

const [savingTable, setSavingTable] =
  useState(false);

const [savingColumn, setSavingColumn] =
  useState(false);

  const openGenerator = () => {
  if (!selectedTable) {
    return;
  }

  setGeneratedPreview(null);
  setGeneratorOpen(true);
};

const generateDefinitionPreview = async () => {
  if (!selectedTable) {
    return;
  }

  try {
    setGeneratingDefinition(true);

    const result = await generateTableDefinition(
      selectedTable.id
    );

    setGeneratedPreview(result);
  } catch (error: any) {
    showMessage(
      error?.response?.data?.detail ??
        "Unable to generate business definitions.",
      "error"
    );
  } finally {
    setGeneratingDefinition(false);
  }
};

const applyDefinition = async () => {
  if (!selectedTable) {
    return;
  }

  try {
    setApplyingDefinition(true);

    const updatedTable =
      await applyGeneratedDefinition(
        selectedTable.id
      );

    setSelectedTable(updatedTable);

    setTables((current) =>
      current.map((table) =>
        table.id === updatedTable.id
          ? {
              ...table,
              business_name:
                updatedTable.business_name,
              description:
                updatedTable.description,
              synonyms:
                updatedTable.synonyms,
              suggested_questions:
                updatedTable.suggested_questions,
              definition_status:
                updatedTable.definition_status,
            }
          : table
      )
    );

    showMessage(
      "Generated definition applied successfully. Review it before approval.",
      "success"
    );
  } catch (error: any) {
    showMessage(
      error?.response?.data?.detail ??
        "Unable to apply generated definitions.",
      "error"
    );
  } finally {
    setApplyingDefinition(false);
  }
};

const approveDefinition = async (
  approved: boolean
) => {
  if (!selectedTable) {
    return;
  }

  try {
    setApprovingDefinition(true);

    const updatedTable =
      await approveGeneratedDefinition(
        selectedTable.id,
        approved
      );

    setSelectedTable(updatedTable);

    setTables((current) =>
      current.map((table) =>
        table.id === updatedTable.id
          ? {
              ...table,
              definition_status:
                updatedTable.definition_status,
            }
          : table
      )
    );

    showMessage(
      approved
        ? "Business definition approved successfully."
        : "Business definition rejected.",
      approved ? "success" : "error"
    );

    setGeneratorOpen(false);
  } catch (error: any) {
    showMessage(
      error?.response?.data?.detail ??
        "Unable to update definition approval.",
      "error"
    );
  } finally {
    setApprovingDefinition(false);
  }
};

const [tableForm, setTableForm] =
  useState<MetadataTableUpdate>({
    business_name: "",
    description: "",
    data_owner: "",
    department: "",
    classification: "internal",
    ai_access_allowed: true,
    is_enabled: true,
  });

const [columnForm, setColumnForm] =
  useState<MetadataColumnUpdate>({
    business_name: "",
    description: "",
    classification: "internal",
    ai_access_allowed: true,
    is_sensitive: false,
    is_enabled: true,
  });

  const openTableEditor = () => {
  if (!selectedTable) {
    return;
  }

  setTableForm({
    business_name:
      selectedTable.business_name ?? "",
    description:
      selectedTable.description ?? "",
    data_owner:
      selectedTable.data_owner ?? "",
    department:
      selectedTable.department ?? "",
    classification:
      selectedTable.classification,
    ai_access_allowed:
      selectedTable.ai_access_allowed,
    is_enabled:
      selectedTable.is_enabled,
  });

  setTableEditorOpen(true);
};

const saveTableDictionary = async () => {
  if (!selectedTable) {
    return;
  }

  try {
    setSavingTable(true);

    const updatedTable = await updateMetadataTable(
      selectedTable.id,
      {
        business_name:
          tableForm.business_name?.trim() || null,
        description:
          tableForm.description?.trim() || null,
        data_owner:
          tableForm.data_owner?.trim() || null,
        department:
          tableForm.department?.trim() || null,
        classification:
          tableForm.classification,
        ai_access_allowed:
          tableForm.ai_access_allowed,
        is_enabled:
          tableForm.is_enabled,
      }
    );

    setSelectedTable(updatedTable);

    setTables((currentTables) =>
      currentTables.map((table) =>
        table.id === updatedTable.id
          ? {
              ...table,
              business_name: updatedTable.business_name,
              description: updatedTable.description,
              data_owner: updatedTable.data_owner,
              department: updatedTable.department,
              classification: updatedTable.classification,
              ai_access_allowed: updatedTable.ai_access_allowed,
              is_enabled: updatedTable.is_enabled,
            }
          : table
      )
    );

    setTableEditorOpen(false);

    showMessage(
      "Table business dictionary updated successfully.",
      "success"
    );
  } catch (error: any) {
    showMessage(
      error?.response?.data?.detail ??
        "Unable to update table information.",
      "error"
    );
  } finally {
    setSavingTable(false);
  }
};

const openColumnEditor = (
  column: MetadataColumn
) => {
  setEditingColumn(column);

  setColumnForm({
    business_name:
      column.business_name ?? "",
    description:
      column.description ?? "",
    classification:
      column.classification,
    ai_access_allowed:
      column.ai_access_allowed,
    is_sensitive:
      column.is_sensitive,
    is_enabled:
      column.is_enabled,
  });

  setColumnEditorOpen(true);
};

const saveColumnDictionary = async () => {
  if (!editingColumn || !selectedTable) {
    return;
  }

  try {
    setSavingColumn(true);

    const updatedColumn =
      await updateMetadataColumn(
        editingColumn.id,
        {
          business_name:
            columnForm.business_name?.trim() ||
            null,
          description:
            columnForm.description?.trim() ||
            null,
          classification:
            columnForm.classification,
          ai_access_allowed:
            columnForm.ai_access_allowed,
          is_sensitive:
            columnForm.is_sensitive,
          is_enabled:
            columnForm.is_enabled,
        }
      );

    setSelectedTable((current) => {
      if (!current) {
        return current;
      }

      return {
        ...current,
        columns: current.columns.map(
          (column) =>
            column.id === updatedColumn.id
              ? updatedColumn
              : column
        ),
      };
    });

    setColumnEditorOpen(false);
    setEditingColumn(null);

    showMessage(
      "Column business dictionary updated successfully.",
      "success"
    );
  } catch (error: any) {
    showMessage(
      error?.response?.data?.detail ??
        "Unable to update column information.",
      "error"
    );
  } finally {
    setSavingColumn(false);
  }
};

  const activeSources = useMemo(
    () =>
      dataSources.filter(
        (source) => source.is_active
      ),
    [dataSources]
  );

  const tableCount = useMemo(
    () =>
      tables.filter(
        (table) => table.object_type === "table"
      ).length,
    [tables]
  );

  const viewCount = useMemo(
    () =>
      tables.filter(
        (table) => table.object_type === "view"
      ).length,
    [tables]
  );

  const showMessage = (
    text: string,
    type: "success" | "error"
  ) => {
    setMessage(text);
    setMessageType(type);
  };

  const loadSources = async () => {
    try {
      setLoadingSources(true);

      const result = await getDataSources();

      setDataSources(result);

      const firstConnectedSource = result.find(
        (source) =>
          source.is_active &&
          source.status === "connected"
      );

      if (firstConnectedSource) {
        setSelectedSourceId(firstConnectedSource.id);
      }
    } catch (error: any) {
      showMessage(
        error?.response?.data?.detail ??
          "Unable to load data sources.",
        "error"
      );
    } finally {
      setLoadingSources(false);
    }
  };

  const loadTables = async (
  sourceId: number,
  searchValue = "",
  clearSelection = true
) => {
  try {
    setLoadingTables(true);

    if (clearSelection) {
      setSelectedTable(null);
    }

      const result = await getMetadataTables(
        sourceId,
        searchValue
      );

      setTables(result);
    } catch (error: any) {
      showMessage(
        error?.response?.data?.detail ??
          "Unable to load metadata.",
        "error"
      );
    } finally {
      setLoadingTables(false);
    }
  };

  useEffect(() => {
    loadSources();
  }, []);

  useEffect(() => {
    if (selectedSourceId !== "") {
      loadTables(selectedSourceId, search);
    } else {
      setTables([]);
      setSelectedTable(null);
    }
  }, [selectedSourceId]);

  const handleSearch = async () => {
    if (selectedSourceId === "") {
      return;
    }

    await loadTables(selectedSourceId, search);
  };

  const handleScan = async () => {
    if (selectedSourceId === "") {
      showMessage(
        "Select a data source first.",
        "error"
      );
      return;
    }

    try {
      setScanning(true);

      const result = await scanMetadata(
        selectedSourceId
      );

      showMessage(
        `${result.message}. ${result.tables_discovered} tables, ${result.views_discovered} views and ${result.columns_discovered} columns discovered.`,
        "success"
      );

      await loadTables(selectedSourceId, search);
    } catch (error: any) {
      showMessage(
        error?.response?.data?.detail ??
          "Metadata scan failed.",
        "error"
      );
    } finally {
      setScanning(false);
    }
  };

  const handleOpenTable = async (
    tableId: number
  ) => {
    try {
      setLoadingTable(true);

      const result = await getMetadataTable(
        tableId
      );

      setSelectedTable(result);
    } catch (error: any) {
      showMessage(
        error?.response?.data?.detail ??
          "Unable to load table details.",
        "error"
      );
    } finally {
      setLoadingTable(false);
    }
  };

  const selectedSource =
    activeSources.find(
      (source) => source.id === selectedSourceId
    ) ?? null;

  return (
    <Box>
      <Box
        sx={{
          mb: 3,
          display: "flex",
          justifyContent: "space-between",
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
            Metadata Explorer
          </Typography>

          <Typography
            sx={{
              mt: 0.7,
              color: "#777777",
            }}
          >
            Explore schemas, tables, views and columns discovered
            from approved enterprise data sources.
          </Typography>
        </Box>

        <Button
          variant="contained"
          disabled={
            scanning ||
            selectedSourceId === ""
          }
          onClick={handleScan}
          sx={{
            px: 3,
            py: 1.15,
            borderRadius: 2.5,
            textTransform: "none",
            fontWeight: 800,
            background:
              "linear-gradient(90deg, #61351f, #c78f2b)",
          }}
        >
          {scanning ? (
            <>
              <CircularProgress
                size={18}
                color="inherit"
                sx={{ mr: 1 }}
              />
              Scanning metadata...
            </>
          ) : (
            "Scan Selected Source"
          )}
        </Button>
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
              md: "minmax(260px, 1fr) minmax(260px, 1fr) auto",
            },
            gap: 2,
            alignItems: "center",
          }}
        >
          <FormControl
            fullWidth
            disabled={loadingSources}
          >
            <InputLabel>Data source</InputLabel>

            <Select
              label="Data source"
              value={selectedSourceId}
              onChange={(event) =>
                setSelectedSourceId(
                  Number(event.target.value)
                )
              }
            >
              {activeSources.map((source) => (
                <MenuItem
                  key={source.id}
                  value={source.id}
                >
                  {source.name} —{" "}
                  {source.database_type.toUpperCase()}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <TextField
            fullWidth
            label="Search tables or descriptions"
            value={search}
            disabled={selectedSourceId === ""}
            onChange={(event) =>
              setSearch(event.target.value)
            }
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                handleSearch();
              }
            }}
          />

          <Button
            variant="outlined"
            disabled={selectedSourceId === ""}
            onClick={handleSearch}
            sx={{
              height: 56,
              px: 3,
              textTransform: "none",
              fontWeight: 800,
              color: "#6b3b21",
              borderColor: "#8d6348",
            }}
          >
            Search
          </Button>
        </Box>
      </Paper>

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
          title="Data Source"
          value={
            selectedSource
              ? selectedSource.name
              : "Not selected"
          }
          description={
            selectedSource
              ? selectedSource.database_type.toUpperCase()
              : "Choose a connected source"
          }
        />

        <SummaryCard
          title="Tables"
          value={String(tableCount)}
          description="Physical database tables"
        />

        <SummaryCard
          title="Views"
          value={String(viewCount)}
          description="Discovered database views"
        />
      </Box>

      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: {
            xs: "1fr",
            xl: "minmax(320px, 0.85fr) minmax(0, 1.65fr)",
          },
          gap: 2.5,
        }}
      >
        <Paper
          elevation={0}
          sx={{
            minHeight: 580,
            borderRadius: 3,
            border: "1px solid #e9e2da",
            overflow: "hidden",
          }}
        >
          <Box
            sx={{
              px: 2.5,
              py: 2,
              borderBottom: "1px solid #eee7df",
            }}
          >
            <Typography
              variant="h6"
              sx={{
                color: "#4f2c1a",
                fontWeight: 800,
              }}
            >
              Database Objects
            </Typography>

            <Typography
              variant="body2"
              sx={{ color: "#888888" }}
            >
              Select a table or view to inspect its columns.
            </Typography>
          </Box>

          <Box
            sx={{
              maxHeight: 650,
              overflowY: "auto",
              p: 1.5,
            }}
          >
            {loadingTables ? (
              <LoadingPanel
                text="Loading metadata..."
              />
            ) : selectedSourceId === "" ? (
              <EmptyPanel
                title="No data source selected"
                description="Select a connected data source to explore its metadata."
              />
            ) : tables.length === 0 ? (
              <EmptyPanel
                title="No metadata available"
                description="Run a metadata scan to discover tables, views and columns."
              />
            ) : (
              tables.map((table) => {
                const selected =
                  selectedTable?.id === table.id;

                return (
                  <Box
                    key={table.id}
                    onClick={() =>
                      handleOpenTable(table.id)
                    }
                    sx={{
                      p: 1.6,
                      mb: 1,
                      cursor: "pointer",
                      borderRadius: 2,
                      border: selected
                        ? "1px solid #d7a94d"
                        : "1px solid transparent",
                      bgcolor: selected
                        ? "#fff3dc"
                        : "#faf8f5",
                      transition: "all 0.18s ease",
                      "&:hover": {
                        transform:
                          "translateX(3px)",
                        borderColor:
                          "#d8bd8e",
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
                          variant="body2"
                          sx={{
                            color: "#4f2c1a",
                            fontWeight: 800,
                            overflow: "hidden",
                            textOverflow:
                              "ellipsis",
                            whiteSpace: "nowrap",
                          }}
                        >
                          {table.business_name ||
                            table.table_name}
                        </Typography>

                        {table.business_name && (
                          <Typography
                            variant="caption"
                            sx={{
                              display: "block",
                              color: "#888888",
                            }}
                          >
                            {table.table_name}
                          </Typography>
                        )}

                        <Typography
                          variant="caption"
                          sx={{
                            display: "block",
                            color: "#999999",
                          }}
                        >
                          {table.schema_name || "Default schema"}
                        </Typography>
                      </Box>

                      <Chip
                        label={
                          table.object_type ===
                          "view"
                            ? "View"
                            : "Table"
                        }
                        size="small"
                        sx={{
                          bgcolor:
                            table.object_type ===
                            "view"
                              ? "#e8eef9"
                              : "#e7f6ed",
                          color:
                            table.object_type ===
                            "view"
                              ? "#315b91"
                              : "#207744",
                          fontWeight: 700,
                        }}
                      />
                    </Box>
                  </Box>
                );
              })
            )}
          </Box>
        </Paper>

        <Paper
          elevation={0}
          sx={{
            minWidth: 0,
            minHeight: 580,
            borderRadius: 3,
            border: "1px solid #e9e2da",
            overflow: "hidden",
          }}
        >
          {loadingTable ? (
            <LoadingPanel
              text="Loading table columns..."
            />
          ) : !selectedTable ? (
            <EmptyPanel
              title="Select a database object"
              description="Choose a table or view from the left panel to inspect its structure."
            />
          ) : (
            <>
              <Box
                sx={{
                  p: 2.5,
                  background:
                    "linear-gradient(135deg, #5b311b 0%, #8c5728 100%)",
                  color: "#ffffff",
                }}
              >
                <Box
                  sx={{
                    display: "flex",
                    justifyContent:
                      "space-between",
                    alignItems:
                      "flex-start",
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
                      {selectedTable.business_name ||
                        selectedTable.table_name}
                    </Typography>

                    <Typography
                      variant="body2"
                      sx={{
                        mt: 0.5,
                        color:
                          "rgba(255,255,255,0.72)",
                      }}
                    >
                      {selectedTable.schema_name
                        ? `${selectedTable.schema_name}.${selectedTable.table_name}`
                        : selectedTable.table_name}
                    </Typography>
                  </Box>

                  <Box
  sx={{
    display: "flex",
    alignItems: "center",
    flexWrap: "wrap",
    gap: 1,
  }}
>
  <Chip
    label={
      selectedTable.object_type === "view"
        ? "Database View"
        : "Database Table"
    }
    sx={{
      bgcolor:
        "rgba(255,255,255,0.14)",
      color: "#ffffff",
      fontWeight: 700,
    }}
  />

  <Button
    variant="contained"
    onClick={openTableEditor}
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
    Edit Business Details
  </Button>

  <Button
  variant="contained"
  onClick={openGenerator}
  sx={{
    bgcolor: "#d6a33a",
    color: "#ffffff",
    textTransform: "none",
    fontWeight: 800,
    "&:hover": {
      bgcolor: "#ba8725",
    },
  }}
>
  Generate with NIBGPT
</Button>

<Chip
  label={
    selectedTable.definition_status === "approved"
      ? "Definition Approved"
      : selectedTable.definition_status === "generated"
        ? "Pending Review"
        : selectedTable.definition_status === "rejected"
          ? "Definition Rejected"
          : "Not Generated"
  }
  sx={{
    bgcolor:
      selectedTable.definition_status === "approved"
        ? "rgba(55,180,105,0.30)"
        : selectedTable.definition_status === "rejected"
          ? "rgba(220,75,75,0.30)"
          : "rgba(255,255,255,0.14)",
    color: "#ffffff",
    fontWeight: 700,
  }}
/>
</Box>
                </Box>

                <Typography
                  variant="body2"
                  sx={{
                    mt: 2,
                    color:
                      "rgba(255,255,255,0.78)",
                  }}
                >
                  {selectedTable.description ||
                    "No business description has been added yet."}
                </Typography>
              </Box>

              <Box
  sx={{
    mt: 2,
    display: "flex",
    flexWrap: "wrap",
    gap: 1,
  }}
>
  <Chip
    label={`Department: ${
      selectedTable.department ||
      "Not assigned"
    }`}
    size="small"
    sx={{
      bgcolor:
        "rgba(255,255,255,0.12)",
      color: "#ffffff",
    }}
  />

  <Chip
    label={`Owner: ${
      selectedTable.data_owner ||
      "Not assigned"
    }`}
    size="small"
    sx={{
      bgcolor:
        "rgba(255,255,255,0.12)",
      color: "#ffffff",
    }}
  />

  <Chip
    label={`Classification: ${selectedTable.classification}`}
    size="small"
    sx={{
      bgcolor:
        "rgba(255,255,255,0.12)",
      color: "#ffffff",
      textTransform: "capitalize",
    }}
  />

  <Chip
    label={
      selectedTable.ai_access_allowed
        ? "AI Access Allowed"
        : "AI Access Blocked"
    }
    size="small"
    sx={{
      bgcolor:
        selectedTable.ai_access_allowed
          ? "rgba(58,180,105,0.28)"
          : "rgba(220,75,75,0.28)",
      color: "#ffffff",
    }}
  />
</Box>

              <Box sx={{ p: 2.5 }}>
                <Typography
                  variant="h6"
                  sx={{
                    mb: 2,
                    color: "#4f2c1a",
                    fontWeight: 800,
                  }}
                >
                  Columns ({selectedTable.columns.length})
                </Typography>

                <TableContainer
                  sx={{
                    maxHeight: 520,
                    border:
                      "1px solid #ece5dd",
                    borderRadius: 2,
                  }}
                >
                  <Table
                    stickyHeader
                    size="small"
                  >
                    <TableHead>
                      <TableRow>
                        <TableCell>
                          Column
                        </TableCell>

                        <TableCell>
                          Data Type
                        </TableCell>

                        <TableCell>
                          Key
                        </TableCell>

                        <TableCell>
                          Nullable
                        </TableCell>

                        <TableCell>
                          Sensitive
                        </TableCell>

                        <TableCell>
                          Action
                        </TableCell>
                      </TableRow>
                    </TableHead>

                    <TableBody>
                      {selectedTable.columns.map(
                        (column) => (
                          <TableRow
                            key={column.id}
                            hover
                          >
                            <TableCell>
                              <Typography
                                variant="body2"
                                sx={{
                                  fontWeight: 800,
                                  color:
                                    "#4f2c1a",
                                }}
                              >
                                {column.business_name ||
                                  column.column_name}
                              </Typography>

                              {column.business_name && (
                                <Typography
                                  variant="caption"
                                  sx={{
                                    color:
                                      "#888888",
                                  }}
                                >
                                  {column.column_name}
                                </Typography>
                              )}
                            </TableCell>

                            <TableCell>
                              <Chip
                                label={
                                  column.data_type
                                }
                                size="small"
                                variant="outlined"
                              />
                            </TableCell>

                            <TableCell>
                              {column.is_primary_key ? (
                                <Chip
                                  label="Primary"
                                  size="small"
                                  sx={{
                                    bgcolor:
                                      "#fff3dc",
                                    color:
                                      "#8b5d12",
                                    fontWeight:
                                      700,
                                  }}
                                />
                              ) : (
                                "—"
                              )}
                            </TableCell>

                            <TableCell>
                              {column.is_nullable
                                ? "Yes"
                                : "No"}
                            </TableCell>

                            <TableCell>
                              {column.is_sensitive ? (
                                <Chip
                                  label="Sensitive"
                                  size="small"
                                  sx={{
                                    bgcolor:
                                      "#fdecec",
                                    color:
                                      "#b3261e",
                                    fontWeight:
                                      700,
                                  }}
                                />
                              ) : (
                                "No"
                              )}
                            </TableCell>
                            <TableCell>
  <Button
    size="small"
    variant="outlined"
    onClick={() =>
      openColumnEditor(column)
    }
    sx={{
      textTransform: "none",
      fontWeight: 700,
      color: "#6b3b21",
      borderColor: "#9f795d",
    }}
  >
    Edit
  </Button>
</TableCell>
                          </TableRow>
                        )
                      )}
                    </TableBody>
                  </Table>
                </TableContainer>
              </Box>
            </>
          )}
        </Paper>
      </Box>

      <Dialog
  open={tableEditorOpen}
  onClose={() => {
    if (!savingTable) {
      setTableEditorOpen(false);
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
    Edit Table Business Dictionary
  </DialogTitle>

  <DialogContent dividers>
    <Alert severity="info" sx={{ mb: 3 }}>
      These business definitions help NIBGPT understand
      natural-language requests and apply governance rules.
    </Alert>

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
        label="Technical table name"
        value={selectedTable?.table_name ?? ""}
        disabled
      />

      <TextField
        label="Business name"
        value={tableForm.business_name ?? ""}
        onChange={(event) =>
          setTableForm((current) => ({
            ...current,
            business_name:
              event.target.value,
          }))
        }
        placeholder="Example: Vehicles"
      />

      <TextField
        label="Department"
        value={tableForm.department ?? ""}
        onChange={(event) =>
          setTableForm((current) => ({
            ...current,
            department:
              event.target.value,
          }))
        }
        placeholder="Example: General Services"
      />

      <TextField
        label="Data owner"
        value={tableForm.data_owner ?? ""}
        onChange={(event) =>
          setTableForm((current) => ({
            ...current,
            data_owner:
              event.target.value,
          }))
        }
        placeholder="Example: Transport Administration"
      />

      <FormControl fullWidth>
        <InputLabel>
          Classification
        </InputLabel>

        <Select
          label="Classification"
          value={
            tableForm.classification ??
            "internal"
          }
          onChange={(event) =>
            setTableForm((current) => ({
              ...current,
              classification:
                event.target
                  .value as DataClassification,
            }))
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

      <Box
        sx={{
          p: 1.5,
          borderRadius: 2,
          bgcolor: "#faf8f5",
        }}
      >
        <FormControlLabel
          control={
            <Switch
              checked={
                tableForm.ai_access_allowed ??
                false
              }
              onChange={(event) =>
                setTableForm((current) => ({
                  ...current,
                  ai_access_allowed:
                    event.target.checked,
                }))
              }
            />
          }
          label="Allow AI access"
        />

        <FormControlLabel
          control={
            <Switch
              checked={
                tableForm.is_enabled ??
                false
              }
              onChange={(event) =>
                setTableForm((current) => ({
                  ...current,
                  is_enabled:
                    event.target.checked,
                }))
              }
            />
          }
          label="Enabled in catalogue"
        />
      </Box>

      <TextField
        multiline
        minRows={4}
        label="Business description"
        value={tableForm.description ?? ""}
        onChange={(event) =>
          setTableForm((current) => ({
            ...current,
            description:
              event.target.value,
          }))
        }
        placeholder="Explain what this table stores and how it is used."
        sx={{
          gridColumn: {
            xs: "auto",
            md: "1 / -1",
          },
        }}
      />
    </Box>
  </DialogContent>

  <DialogActions sx={{ px: 3, py: 2 }}>
    <Button
      disabled={savingTable}
      onClick={() =>
        setTableEditorOpen(false)
      }
      sx={{
        textTransform: "none",
      }}
    >
      Cancel
    </Button>

    <Button
      variant="contained"
      disabled={savingTable}
      onClick={saveTableDictionary}
      sx={{
        px: 3,
        textTransform: "none",
        fontWeight: 800,
        background:
          "linear-gradient(90deg, #61351f, #c78f2b)",
      }}
    >
      {savingTable
        ? "Saving..."
        : "Save Business Details"}
    </Button>
  </DialogActions>
</Dialog>

<Dialog
  open={columnEditorOpen}
  onClose={() => {
    if (!savingColumn) {
      setColumnEditorOpen(false);
      setEditingColumn(null);
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
    Edit Column Business Dictionary
  </DialogTitle>

  <DialogContent dividers>
    <Box
      sx={{
        display: "grid",
        gap: 2,
      }}
    >
      <TextField
        label="Technical column name"
        value={
          editingColumn?.column_name ?? ""
        }
        disabled
      />

      <TextField
        label="Data type"
        value={
          editingColumn?.data_type ?? ""
        }
        disabled
      />

      <TextField
        label="Business name"
        value={
          columnForm.business_name ?? ""
        }
        onChange={(event) =>
          setColumnForm((current) => ({
            ...current,
            business_name:
              event.target.value,
          }))
        }
        placeholder="Example: Assignment Status"
      />

      <FormControl fullWidth>
        <InputLabel>
          Classification
        </InputLabel>

        <Select
          label="Classification"
          value={
            columnForm.classification ??
            "internal"
          }
          onChange={(event) =>
            setColumnForm((current) => ({
              ...current,
              classification:
                event.target
                  .value as DataClassification,
            }))
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
        multiline
        minRows={4}
        label="Business description"
        value={
          columnForm.description ?? ""
        }
        onChange={(event) =>
          setColumnForm((current) => ({
            ...current,
            description:
              event.target.value,
          }))
        }
        placeholder="Explain the business meaning of this field."
      />

      <Paper
        elevation={0}
        sx={{
          p: 2,
          bgcolor: "#faf8f5",
          border: "1px solid #ece4db",
        }}
      >
        <FormControlLabel
          control={
            <Checkbox
              checked={
                columnForm.is_sensitive ??
                false
              }
              onChange={(event) =>
                setColumnForm((current) => ({
                  ...current,
                  is_sensitive:
                    event.target.checked,
                }))
              }
            />
          }
          label="Contains sensitive information"
        />

        <FormControlLabel
          control={
            <Checkbox
              checked={
                columnForm.ai_access_allowed ??
                false
              }
              onChange={(event) =>
                setColumnForm((current) => ({
                  ...current,
                  ai_access_allowed:
                    event.target.checked,
                }))
              }
            />
          }
          label="Allow AI access"
        />

        <FormControlLabel
          control={
            <Checkbox
              checked={
                columnForm.is_enabled ??
                false
              }
              onChange={(event) =>
                setColumnForm((current) => ({
                  ...current,
                  is_enabled:
                    event.target.checked,
                }))
              }
            />
          }
          label="Enabled in catalogue"
        />
      </Paper>
    </Box>
  </DialogContent>

  <DialogActions sx={{ px: 3, py: 2 }}>
    <Button
      disabled={savingColumn}
      onClick={() => {
        setColumnEditorOpen(false);
        setEditingColumn(null);
      }}
      sx={{
        textTransform: "none",
      }}
    >
      Cancel
    </Button>

    <Button
      variant="contained"
      disabled={savingColumn}
      onClick={saveColumnDictionary}
      sx={{
        px: 3,
        textTransform: "none",
        fontWeight: 800,
        background:
          "linear-gradient(90deg, #61351f, #c78f2b)",
      }}
    >
      {savingColumn
        ? "Saving..."
        : "Save Column Details"}
    </Button>
  </DialogActions>
</Dialog>

<GenerateDefinitionDialog
  open={generatorOpen}
  table={selectedTable}
  preview={generatedPreview}
  generating={generatingDefinition}
  applying={applyingDefinition}
  approving={approvingDefinition}
  onClose={() => {
    setGeneratorOpen(false);
    setGeneratedPreview(null);
  }}
  onGenerate={generateDefinitionPreview}
  onApply={applyDefinition}
  onApprove={approveDefinition}
  onEdit={() => {
    setGeneratorOpen(false);
    setGeneratedPreview(null);

    setTimeout(() => {
      openTableEditor();
    }, 100);
  }}
/>

      <Snackbar
        open={Boolean(message)}
        autoHideDuration={6000}
        onClose={() => setMessage("")}
        anchorOrigin={{
          vertical: "bottom",
          horizontal: "right",
        }}
      >
        <Alert
          severity={messageType}
          variant="filled"
          onClose={() => setMessage("")}
          sx={{ width: "100%" }}
        >
          {message}
        </Alert>
      </Snackbar>
    </Box>
  );
}


interface SummaryCardProps {
  title: string;
  value: string;
  description: string;
}

function SummaryCard({
  title,
  value,
  description,
}: SummaryCardProps) {
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
        {title}
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
        sx={{ color: "#999999" }}
      >
        {description}
      </Typography>
    </Paper>
  );
}


interface EmptyPanelProps {
  title: string;
  description: string;
}

function EmptyPanel({
  title,
  description,
}: EmptyPanelProps) {
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
            width: 76,
            height: 76,
            mx: "auto",
            mb: 2,
            borderRadius: 3,
            display: "grid",
            placeItems: "center",
            bgcolor: "#fff3dc",
            color: "#8b5d12",
            fontSize: "1.35rem",
            fontWeight: 900,
          }}
        >
          DB
        </Box>

        <Typography
          variant="h6"
          sx={{
            color: "#4f2c1a",
            fontWeight: 800,
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


interface LoadingPanelProps {
  text: string;
}

function LoadingPanel({
  text,
}: LoadingPanelProps) {
  return (
    <Box
      sx={{
        minHeight: 430,
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
          {text}
        </Typography>
      </Box>
    </Box>
  );
}

export default MetadataExplorerPage;
