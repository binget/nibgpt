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
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Snackbar,
  Switch,
  TextField,
  Typography,
} from "@mui/material";
import { FormEvent, useEffect, useMemo, useState } from "react";

import {
  createDataSource,
  deleteDataSource,
  getDataSources,
  testDataSource,
} from "../../services/dataSources";

import type {
  DataSource,
  DataSourceCreate,
  DatabaseType,
} from "../../types/dataSource";

const initialForm: DataSourceCreate = {
  name: "",
  code: "",
  database_type: "postgresql",
  host: "",
  port: 5432,
  database_name: "",
  service_name: "",
  username: "",
  password: "",
  description: "",
  is_active: true,
};

function DataSourcesPage() {
  const [dataSources, setDataSources] = useState<DataSource[]>([]);
  const [formData, setFormData] =
    useState<DataSourceCreate>(initialForm);

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testingId, setTestingId] = useState<number | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);

  const [dialogOpen, setDialogOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] =
    useState<DataSource | null>(null);

  const [message, setMessage] = useState("");
  const [messageType, setMessageType] =
    useState<"success" | "error">("success");

  const connectedCount = useMemo(
    () =>
      dataSources.filter(
        (source) => source.status === "connected"
      ).length,
    [dataSources]
  );

  const failedCount = useMemo(
    () =>
      dataSources.filter(
        (source) => source.status === "failed"
      ).length,
    [dataSources]
  );

  const showMessage = (
    text: string,
    type: "success" | "error"
  ) => {
    setMessage(text);
    setMessageType(type);
  };

  const loadDataSources = async () => {
    try {
      setLoading(true);
      const result = await getDataSources();
      setDataSources(result);
    } catch (error: any) {
      showMessage(
        error?.response?.data?.detail ??
          "Unable to load data sources.",
        "error"
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDataSources();
  }, []);

  const handleDatabaseTypeChange = (
    databaseType: DatabaseType
  ) => {
    let defaultPort = 5432;

    if (databaseType === "mysql") {
      defaultPort = 3306;
    }

    if (databaseType === "oracle") {
      defaultPort = 1521;
    }

    setFormData((current) => ({
      ...current,
      database_type: databaseType,
      port: defaultPort,
      database_name:
        databaseType === "oracle"
          ? ""
          : current.database_name,
      service_name:
        databaseType === "oracle"
          ? current.service_name
          : "",
    }));
  };

  const handleOpenDialog = () => {
    setFormData(initialForm);
    setDialogOpen(true);
  };

  const handleCloseDialog = () => {
    if (!saving) {
      setDialogOpen(false);
    }
  };

  const handleCreate = async (
    event: FormEvent<HTMLFormElement>
  ) => {
    event.preventDefault();

    if (
      !formData.name.trim() ||
      !formData.code.trim() ||
      !formData.host.trim() ||
      !formData.username.trim() ||
      !formData.password
    ) {
      showMessage(
        "Please complete all required fields.",
        "error"
      );
      return;
    }

    if (
      formData.database_type === "oracle" &&
      !formData.service_name?.trim()
    ) {
      showMessage(
        "Oracle service name is required.",
        "error"
      );
      return;
    }

    if (
      formData.database_type !== "oracle" &&
      !formData.database_name?.trim()
    ) {
      showMessage(
        "Database name is required.",
        "error"
      );
      return;
    }

    try {
      setSaving(true);

      await createDataSource({
        ...formData,
        name: formData.name.trim(),
        code: formData.code.trim().toUpperCase(),
        host: formData.host.trim(),
        username: formData.username.trim(),
        database_name:
          formData.database_type === "oracle"
            ? null
            : formData.database_name?.trim() || null,
        service_name:
          formData.database_type === "oracle"
            ? formData.service_name?.trim() || null
            : null,
        description:
          formData.description?.trim() || null,
      });

      setDialogOpen(false);
      setFormData(initialForm);

      showMessage(
        "Data source created successfully.",
        "success"
      );

      await loadDataSources();
    } catch (error: any) {
      showMessage(
        error?.response?.data?.detail ??
          "Unable to create data source.",
        "error"
      );
    } finally {
      setSaving(false);
    }
  };

  const handleTest = async (source: DataSource) => {
    try {
      setTestingId(source.id);

      const result = await testDataSource(source.id);

      showMessage(
        result.message,
        result.success ? "success" : "error"
      );

      await loadDataSources();
    } catch (error: any) {
      showMessage(
        error?.response?.data?.detail ??
          "Connection test failed.",
        "error"
      );
    } finally {
      setTestingId(null);
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) {
      return;
    }

    try {
      setDeletingId(deleteTarget.id);

      await deleteDataSource(deleteTarget.id);

      showMessage(
        "Data source deleted successfully.",
        "success"
      );

      setDeleteTarget(null);
      await loadDataSources();
    } catch (error: any) {
      showMessage(
        error?.response?.data?.detail ??
          "Unable to delete data source.",
        "error"
      );
    } finally {
      setDeletingId(null);
    }
  };

  const statusChip = (status: DataSource["status"]) => {
    if (status === "connected") {
      return (
        <Chip
          label="Connected"
          size="small"
          sx={{
            bgcolor: "#e7f6ed",
            color: "#207744",
            fontWeight: 700,
          }}
        />
      );
    }

    if (status === "failed") {
      return (
        <Chip
          label="Failed"
          size="small"
          sx={{
            bgcolor: "#fdecec",
            color: "#b3261e",
            fontWeight: 700,
          }}
        />
      );
    }

    return (
      <Chip
        label="Not tested"
        size="small"
        sx={{
          bgcolor: "#fff4dc",
          color: "#8b5d12",
          fontWeight: 700,
        }}
      />
    );
  };

  const databaseLabel = (type: DatabaseType) => {
    if (type === "postgresql") {
      return "PostgreSQL";
    }

    if (type === "mysql") {
      return "MySQL";
    }

    return "Oracle";
  };

  const databaseSymbol = (type: DatabaseType) => {
    if (type === "postgresql") {
      return "PG";
    }

    if (type === "mysql") {
      return "MY";
    }

    return "OR";
  };

  const formatDate = (value: string | null) => {
    if (!value) {
      return "Never tested";
    }

    return new Date(value).toLocaleString();
  };

  return (
    <Box>
      <Box
        sx={{
          mb: 3,
          display: "flex",
          alignItems: {
            xs: "flex-start",
            md: "center",
          },
          justifyContent: "space-between",
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
            Data Sources
          </Typography>

          <Typography sx={{ mt: 0.7, color: "#777777" }}>
            Manage secure Oracle, MySQL and PostgreSQL
            connections used by NIBGPT.
          </Typography>
        </Box>

        <Button
          variant="contained"
          onClick={handleOpenDialog}
          sx={{
            px: 3,
            py: 1.1,
            borderRadius: 2.5,
            textTransform: "none",
            fontWeight: 700,
            background:
              "linear-gradient(90deg, #61351f, #c78f2b)",
          }}
        >
          + Add Data Source
        </Button>
      </Box>

      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: {
            xs: "1fr",
            sm: "repeat(3, 1fr)",
          },
          gap: 2,
          mb: 3,
        }}
      >
        <SummaryCard
          title="Total Sources"
          value={dataSources.length}
          description="Registered database connections"
        />

        <SummaryCard
          title="Connected"
          value={connectedCount}
          description="Successful connection tests"
        />

        <SummaryCard
          title="Failed"
          value={failedCount}
          description="Connections requiring attention"
        />
      </Box>

      {loading ? (
        <Paper
          elevation={0}
          sx={{
            minHeight: 260,
            border: "1px solid #e9e2da",
            borderRadius: 3,
            display: "grid",
            placeItems: "center",
          }}
        >
          <Box sx={{ textAlign: "center" }}>
            <CircularProgress sx={{ color: "#a97826" }} />

            <Typography sx={{ mt: 2, color: "#777777" }}>
              Loading data sources...
            </Typography>
          </Box>
        </Paper>
      ) : dataSources.length === 0 ? (
        <Paper
          elevation={0}
          sx={{
            p: 6,
            textAlign: "center",
            borderRadius: 3,
            border: "1px solid #e9e2da",
          }}
        >
          <Box
            sx={{
              width: 82,
              height: 82,
              mx: "auto",
              mb: 2,
              borderRadius: 3,
              display: "grid",
              placeItems: "center",
              bgcolor: "#fff4dc",
              color: "#8b5d12",
              fontSize: "1.6rem",
              fontWeight: 900,
            }}
          >
            DB
          </Box>

          <Typography
            variant="h5"
            sx={{ fontWeight: 800, color: "#4f2c1a" }}
          >
            No data sources registered
          </Typography>

          <Typography sx={{ mt: 1, color: "#777777" }}>
            Add the first database connection to begin connecting
            NIBGPT with approved banking systems.
          </Typography>
        </Paper>
      ) : (
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: {
              xs: "1fr",
              lg: "repeat(2, minmax(0, 1fr))",
            },
            gap: 2.5,
          }}
        >
          {dataSources.map((source) => (
            <Paper
              key={source.id}
              elevation={0}
              sx={{
                p: 3,
                borderRadius: 3,
                border: "1px solid #e9e2da",
                transition:
                  "transform 0.2s ease, box-shadow 0.2s ease",
                "&:hover": {
                  transform: "translateY(-3px)",
                  boxShadow:
                    "0 14px 32px rgba(80, 45, 24, 0.10)",
                },
              }}
            >
              <Box
                sx={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "flex-start",
                  gap: 2,
                }}
              >
                <Box
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    gap: 2,
                  }}
                >
                  <Box
                    sx={{
                      width: 54,
                      height: 54,
                      borderRadius: 2.5,
                      display: "grid",
                      placeItems: "center",
                      color: "#ffffff",
                      fontWeight: 900,
                      background:
                        "linear-gradient(145deg, #60351f, #d3a034)",
                    }}
                  >
                    {databaseSymbol(source.database_type)}
                  </Box>

                  <Box>
                    <Typography
                      variant="h6"
                      sx={{
                        color: "#4f2c1a",
                        fontWeight: 800,
                      }}
                    >
                      {source.name}
                    </Typography>

                    <Typography
                      variant="body2"
                      sx={{ color: "#888888" }}
                    >
                      {source.code}
                    </Typography>
                  </Box>
                </Box>

                {statusChip(source.status)}
              </Box>

              <Box
                sx={{
                  mt: 3,
                  p: 2,
                  borderRadius: 2,
                  bgcolor: "#faf8f5",
                  display: "grid",
                  gridTemplateColumns: {
                    xs: "1fr",
                    sm: "repeat(2, 1fr)",
                  },
                  gap: 1.5,
                }}
              >
                <InformationRow
                  label="Database"
                  value={databaseLabel(source.database_type)}
                />

                <InformationRow
                  label="Host"
                  value={`${source.host}:${source.port}`}
                />

                <InformationRow
                  label={
                    source.database_type === "oracle"
                      ? "Service"
                      : "Database"
                  }
                  value={
                    source.database_type === "oracle"
                      ? source.service_name || "-"
                      : source.database_name || "-"
                  }
                />

                <InformationRow
                  label="Username"
                  value={source.username}
                />

                <InformationRow
                  label="Active"
                  value={source.is_active ? "Yes" : "No"}
                />

                <InformationRow
                  label="Last tested"
                  value={formatDate(source.last_tested_at)}
                />
              </Box>

              {source.last_test_message && (
                <Alert
                  severity={
                    source.status === "connected"
                      ? "success"
                      : "error"
                  }
                  sx={{ mt: 2 }}
                >
                  {source.last_test_message}
                </Alert>
              )}

              {source.description && (
                <Typography
                  variant="body2"
                  sx={{
                    mt: 2,
                    color: "#777777",
                    lineHeight: 1.7,
                  }}
                >
                  {source.description}
                </Typography>
              )}

              <Box
                sx={{
                  mt: 3,
                  display: "flex",
                  justifyContent: "flex-end",
                  flexWrap: "wrap",
                  gap: 1,
                }}
              >
                <Button
                  variant="outlined"
                  disabled={testingId === source.id}
                  onClick={() => handleTest(source)}
                  sx={{
                    textTransform: "none",
                    fontWeight: 700,
                    color: "#6b3b21",
                    borderColor: "#8d6348",
                  }}
                >
                  {testingId === source.id ? (
                    <>
                      <CircularProgress
                        size={18}
                        sx={{
                          mr: 1,
                          color: "#6b3b21",
                        }}
                      />
                      Testing...
                    </>
                  ) : (
                    "Test Connection"
                  )}
                </Button>

                <Button
                  variant="outlined"
                  color="error"
                  onClick={() => setDeleteTarget(source)}
                  sx={{
                    textTransform: "none",
                    fontWeight: 700,
                  }}
                >
                  Delete
                </Button>
              </Box>
            </Paper>
          ))}
        </Box>
      )}

      <Dialog
        open={dialogOpen}
        onClose={handleCloseDialog}
        fullWidth
        maxWidth="md"
      >
        <Box component="form" onSubmit={handleCreate}>
          <DialogTitle
            sx={{
              color: "#4f2c1a",
              fontWeight: 900,
            }}
          >
            Add Data Source
          </DialogTitle>

          <DialogContent dividers>
            <Alert severity="info" sx={{ mb: 3 }}>
              Database credentials are encrypted by the backend.
              Passwords are never returned to the browser.
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
                required
                label="Data source name"
                value={formData.name}
                onChange={(event) =>
                  setFormData((current) => ({
                    ...current,
                    name: event.target.value,
                  }))
                }
              />

              <TextField
                required
                label="Code"
                value={formData.code}
                onChange={(event) =>
                  setFormData((current) => ({
                    ...current,
                    code: event.target.value.toUpperCase(),
                  }))
                }
                helperText="Example: T24_REPORTING"
              />

              <FormControl required>
                <InputLabel>Database type</InputLabel>

                <Select
                  label="Database type"
                  value={formData.database_type}
                  onChange={(event) =>
                    handleDatabaseTypeChange(
                      event.target.value as DatabaseType
                    )
                  }
                >
                  <MenuItem value="postgresql">
                    PostgreSQL
                  </MenuItem>

                  <MenuItem value="mysql">MySQL</MenuItem>

                  <MenuItem value="oracle">Oracle</MenuItem>
                </Select>
              </FormControl>

              <TextField
                required
                label="Host or IP address"
                value={formData.host}
                onChange={(event) =>
                  setFormData((current) => ({
                    ...current,
                    host: event.target.value,
                  }))
                }
              />

              <TextField
                required
                type="number"
                label="Port"
                value={formData.port}
                onChange={(event) =>
                  setFormData((current) => ({
                    ...current,
                    port: Number(event.target.value),
                  }))
                }
              />

              {formData.database_type === "oracle" ? (
                <TextField
                  required
                  label="Oracle service name"
                  value={formData.service_name ?? ""}
                  onChange={(event) =>
                    setFormData((current) => ({
                      ...current,
                      service_name: event.target.value,
                    }))
                  }
                  helperText="Example: T24PROD"
                />
              ) : (
                <TextField
                  required
                  label="Database name"
                  value={formData.database_name ?? ""}
                  onChange={(event) =>
                    setFormData((current) => ({
                      ...current,
                      database_name: event.target.value,
                    }))
                  }
                />
              )}

              <TextField
                required
                label="Username"
                value={formData.username}
                onChange={(event) =>
                  setFormData((current) => ({
                    ...current,
                    username: event.target.value,
                  }))
                }
              />

              <TextField
                required
                type="password"
                label="Password"
                value={formData.password}
                onChange={(event) =>
                  setFormData((current) => ({
                    ...current,
                    password: event.target.value,
                  }))
                }
                autoComplete="new-password"
              />

              <TextField
                multiline
                minRows={3}
                label="Description"
                value={formData.description ?? ""}
                onChange={(event) =>
                  setFormData((current) => ({
                    ...current,
                    description: event.target.value,
                  }))
                }
                sx={{
                  gridColumn: {
                    xs: "auto",
                    md: "1 / -1",
                  },
                }}
              />

              <Box
                sx={{
                  gridColumn: {
                    xs: "auto",
                    md: "1 / -1",
                  },
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  p: 2,
                  borderRadius: 2,
                  bgcolor: "#faf8f5",
                }}
              >
                <Box>
                  <Typography sx={{ fontWeight: 700 }}>
                    Active data source
                  </Typography>

                  <Typography
                    variant="body2"
                    sx={{ color: "#777777" }}
                  >
                    Inactive sources cannot be used by NIBGPT.
                  </Typography>
                </Box>

                <Switch
                  checked={formData.is_active}
                  onChange={(event) =>
                    setFormData((current) => ({
                      ...current,
                      is_active: event.target.checked,
                    }))
                  }
                />
              </Box>
            </Box>
          </DialogContent>

          <DialogActions sx={{ px: 3, py: 2 }}>
            <Button
              onClick={handleCloseDialog}
              disabled={saving}
              sx={{
                color: "#666666",
                textTransform: "none",
              }}
            >
              Cancel
            </Button>

            <Button
              type="submit"
              variant="contained"
              disabled={saving}
              sx={{
                px: 3,
                textTransform: "none",
                fontWeight: 700,
                background:
                  "linear-gradient(90deg, #61351f, #c78f2b)",
              }}
            >
              {saving ? (
                <>
                  <CircularProgress
                    size={18}
                    color="inherit"
                    sx={{ mr: 1 }}
                  />
                  Saving...
                </>
              ) : (
                "Save Data Source"
              )}
            </Button>
          </DialogActions>
        </Box>
      </Dialog>

      <Dialog
        open={Boolean(deleteTarget)}
        onClose={() => {
          if (!deletingId) {
            setDeleteTarget(null);
          }
        }}
        maxWidth="xs"
        fullWidth
      >
        <DialogTitle sx={{ fontWeight: 800 }}>
          Delete Data Source
        </DialogTitle>

        <DialogContent>
          <Typography>
            Are you sure you want to delete{" "}
            <strong>{deleteTarget?.name}</strong>?
          </Typography>

          <Alert severity="warning" sx={{ mt: 2 }}>
            This action removes the saved connection configuration.
          </Alert>
        </DialogContent>

        <DialogActions>
          <Button
            onClick={() => setDeleteTarget(null)}
            disabled={Boolean(deletingId)}
            sx={{ textTransform: "none" }}
          >
            Cancel
          </Button>

          <Button
            variant="contained"
            color="error"
            disabled={Boolean(deletingId)}
            onClick={handleDelete}
            sx={{ textTransform: "none" }}
          >
            {deletingId ? "Deleting..." : "Delete"}
          </Button>
        </DialogActions>
      </Dialog>

      <Snackbar
        open={Boolean(message)}
        autoHideDuration={5000}
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
  value: number;
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
        variant="h3"
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
        sx={{ color: "#999999" }}
      >
        {description}
      </Typography>
    </Paper>
  );
}

interface InformationRowProps {
  label: string;
  value: string;
}

function InformationRow({
  label,
  value,
}: InformationRowProps) {
  return (
    <Box>
      <Typography
        variant="caption"
        sx={{
          color: "#999999",
          fontWeight: 700,
        }}
      >
        {label}
      </Typography>

      <Typography
        variant="body2"
        sx={{
          mt: 0.3,
          color: "#454545",
          fontWeight: 600,
          wordBreak: "break-word",
        }}
      >
        {value}
      </Typography>
    </Box>
  );
}

export default DataSourcesPage;
