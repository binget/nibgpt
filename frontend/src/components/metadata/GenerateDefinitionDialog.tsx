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
  Divider,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";

import type {
  GeneratedTableDefinition,
  MetadataTableDetail,
} from "../../types/metadata";

interface GenerateDefinitionDialogProps {
   open: boolean;
  table: MetadataTableDetail | null;
  preview: GeneratedTableDefinition | null;
  generating: boolean;
  applying: boolean;
  approving: boolean;
  onClose: () => void;
  onGenerate: () => void;
  onApply: () => void;
  onApprove: (approved: boolean) => void;
  onEdit: () => void;
}

function GenerateDefinitionDialog({
  open,
  table,
  preview,
  generating,
  applying,
  approving,
  onClose,
  onGenerate,
  onApply,
  onApprove,
  onEdit,
}: GenerateDefinitionDialogProps) {
  const busy =
    generating || applying || approving;

  const status = table?.definition_status ?? "not_generated";

  return (
    <Dialog
      open={open}
      onClose={() => {
        if (!busy) {
          onClose();
        }
      }}
      fullWidth
      maxWidth="lg"
    >
      <DialogTitle
        sx={{
          color: "#4f2c1a",
          fontWeight: 900,
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          gap: 2,
        }}
      >
        <Box>
          NIBGPT Business Dictionary Generator

          <Typography
            variant="body2"
            sx={{
              mt: 0.5,
              color: "#777777",
              fontWeight: 400,
            }}
          >
            Review generated definitions before applying them.
          </Typography>
        </Box>

        <DefinitionStatusChip status={status} />
      </DialogTitle>

      <DialogContent dividers>
        {!table ? (
          <Alert severity="warning">
            No metadata table is selected.
          </Alert>
        ) : (
          <>
            <Paper
              elevation={0}
              sx={{
                p: 2.5,
                mb: 2.5,
                borderRadius: 3,
                color: "#ffffff",
                background:
                  "linear-gradient(135deg, #5b311b, #9c682d)",
              }}
            >
              <Typography
                variant="caption"
                sx={{
                  color: "rgba(255,255,255,0.68)",
                  fontWeight: 700,
                }}
              >
                TECHNICAL TABLE
              </Typography>

              <Typography
                variant="h5"
                sx={{
                  mt: 0.5,
                  fontWeight: 900,
                }}
              >
                {table.schema_name
                  ? `${table.schema_name}.${table.table_name}`
                  : table.table_name}
              </Typography>

              <Typography
                sx={{
                  mt: 1,
                  color: "rgba(255,255,255,0.78)",
                }}
              >
                NIBGPT analyses the table name, columns, data
                types, primary keys and existing definitions.
              </Typography>
            </Paper>

            {!preview ? (
              <Box
                sx={{
                  minHeight: 350,
                  display: "grid",
                  placeItems: "center",
                  textAlign: "center",
                }}
              >
                <Box>
                  <Box
                    sx={{
                      width: 86,
                      height: 86,
                      mx: "auto",
                      mb: 2,
                      borderRadius: 4,
                      display: "grid",
                      placeItems: "center",
                      color: "#ffffff",
                      fontWeight: 900,
                      fontSize: "1.25rem",
                      background:
                        "linear-gradient(145deg, #60351f, #d3a034)",
                    }}
                  >
                    AI
                  </Box>

                  <Typography
                    variant="h5"
                    sx={{
                      color: "#4f2c1a",
                      fontWeight: 900,
                    }}
                  >
                    Ready to analyse this table
                  </Typography>

                  <Typography
                    sx={{
                      mt: 1,
                      color: "#777777",
                      maxWidth: 520,
                    }}
                  >
                    Generate a suggested business name,
                    description, synonyms, questions and column
                    definitions.
                  </Typography>

                  <Button
                    variant="contained"
                    disabled={generating}
                    onClick={onGenerate}
                    sx={{
                      mt: 3,
                      px: 4,
                      py: 1.2,
                      borderRadius: 2.5,
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
                        Analysing table...
                      </>
                    ) : (
                      "Generate with NIBGPT"
                    )}
                  </Button>
                </Box>
              </Box>
            ) : (
              <Box>
                <Alert severity="info" sx={{ mb: 2.5 }}>
                  This is a generated preview. Nothing is saved
                  until you click <strong>Apply Definition</strong>.
                </Alert>

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
                  <DefinitionPanel
                    label="Suggested Business Name"
                    value={preview.business_name}
                  />

                  <DefinitionPanel
                    label="Technical Name"
                    value={preview.technical_name}
                  />
                </Box>

                <DefinitionPanel
                  label="Suggested Description"
                  value={preview.description}
                  sx={{ mt: 2 }}
                />

                <Box
                  sx={{
                    display: "grid",
                    gridTemplateColumns: {
                      xs: "1fr",
                      md: "repeat(2, minmax(0, 1fr))",
                    },
                    gap: 2,
                    mt: 2,
                  }}
                >
                  <Paper
                    elevation={0}
                    sx={{
                      p: 2.5,
                      borderRadius: 3,
                      border: "1px solid #e9e2da",
                    }}
                  >
                    <Typography
                      sx={{
                        color: "#4f2c1a",
                        fontWeight: 800,
                      }}
                    >
                      Suggested Synonyms
                    </Typography>

                    <Box
                      sx={{
                        mt: 1.5,
                        display: "flex",
                        flexWrap: "wrap",
                        gap: 1,
                      }}
                    >
                      {preview.synonyms.map((synonym) => (
                        <Chip
                          key={synonym}
                          label={synonym}
                          size="small"
                          sx={{
                            bgcolor: "#fff3dc",
                            color: "#7d5417",
                            fontWeight: 700,
                          }}
                        />
                      ))}
                    </Box>
                  </Paper>

                  <Paper
                    elevation={0}
                    sx={{
                      p: 2.5,
                      borderRadius: 3,
                      border: "1px solid #e9e2da",
                    }}
                  >
                    <Typography
                      sx={{
                        color: "#4f2c1a",
                        fontWeight: 800,
                      }}
                    >
                      Suggested Questions
                    </Typography>

                    <Box
                      component="ul"
                      sx={{
                        mt: 1.5,
                        mb: 0,
                        pl: 2.5,
                        color: "#555555",
                      }}
                    >
                      {preview.suggested_questions.map(
                        (question) => (
                          <Box
                            component="li"
                            key={question}
                            sx={{ mb: 0.8 }}
                          >
                            {question}
                          </Box>
                        )
                      )}
                    </Box>
                  </Paper>
                </Box>

                <Divider sx={{ my: 3 }} />

                <Typography
                  variant="h6"
                  sx={{
                    color: "#4f2c1a",
                    fontWeight: 900,
                    mb: 1.5,
                  }}
                >
                  Generated Column Definitions
                </Typography>

                <TableContainer
                  sx={{
                    border: "1px solid #e9e2da",
                    borderRadius: 2,
                    maxHeight: 460,
                  }}
                >
                  <Table stickyHeader size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Technical Name</TableCell>
                        <TableCell>Business Name</TableCell>
                        <TableCell>Description</TableCell>
                        <TableCell>Classification</TableCell>
                        <TableCell>Sensitive</TableCell>
                      </TableRow>
                    </TableHead>

                    <TableBody>
                      {preview.columns.map((column) => (
                        <TableRow key={column.column_id} hover>
                          <TableCell>
                            <Typography
                              variant="body2"
                              sx={{ fontWeight: 700 }}
                            >
                              {column.technical_name}
                            </Typography>
                          </TableCell>

                          <TableCell>
                            {column.business_name}
                          </TableCell>

                          <TableCell
                            sx={{
                              minWidth: 300,
                              color: "#666666",
                            }}
                          >
                            {column.description}
                          </TableCell>

                          <TableCell>
                            <Chip
                              label={column.classification}
                              size="small"
                              sx={{
                                textTransform: "capitalize",
                              }}
                            />
                          </TableCell>

                          <TableCell>
                            {column.is_sensitive ? (
                              <Chip
                                label="Sensitive"
                                size="small"
                                sx={{
                                  bgcolor: "#fdecec",
                                  color: "#b3261e",
                                  fontWeight: 700,
                                }}
                              />
                            ) : (
                              "No"
                            )}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              </Box>
            )}
          </>
        )}
      </DialogContent>

      <DialogActions
        sx={{
          px: 3,
          py: 2,
          flexWrap: "wrap",
          gap: 1,
        }}
      >
        <Button
          disabled={busy}
          onClick={onClose}
          sx={{ textTransform: "none" }}
        >
          Close
        </Button>

        {preview && (
          <>
            <Button
              variant="outlined"
              disabled={busy}
              onClick={onGenerate}
              sx={{
                textTransform: "none",
                color: "#6b3b21",
                borderColor: "#9e795e",
                fontWeight: 700,
              }}
            >
              Generate Again
            </Button>

            <Button
              variant="contained"
              disabled={busy}
              onClick={onApply}
              sx={{
                textTransform: "none",
                fontWeight: 800,
                background:
                  "linear-gradient(90deg, #61351f, #c78f2b)",
              }}
            >
              {applying ? "Applying..." : "Apply Definition"}
            </Button>
          </>
        )}

        {status === "generated" && (
  <Button
    variant="outlined"
    disabled={busy}
    onClick={onEdit}
    sx={{
      textTransform: "none",
      fontWeight: 800,
      color: "#6b3b21",
      borderColor: "#9e795e",
    }}
  >
    Edit Manually
  </Button>
)}

        {status === "generated" && (
          <>
            <Button
              variant="outlined"
              color="error"
              disabled={busy}
              onClick={() => onApprove(false)}
              sx={{
                textTransform: "none",
                fontWeight: 700,
              }}
            >
              Reject
            </Button>

            <Button
              variant="contained"
              disabled={busy}
              onClick={() => onApprove(true)}
              sx={{
                textTransform: "none",
                fontWeight: 800,
                bgcolor: "#28774b",
                "&:hover": {
                  bgcolor: "#1f623d",
                },
              }}
            >
              {approving ? "Approving..." : "Approve"}
            </Button>
          </>
        )}
      </DialogActions>
    </Dialog>
  );
}

interface DefinitionPanelProps {
  label: string;
  value: string;
  sx?: object;
}

function DefinitionPanel({
  label,
  value,
  sx,
}: DefinitionPanelProps) {
  return (
    <Paper
      elevation={0}
      sx={{
        p: 2.5,
        borderRadius: 3,
        border: "1px solid #e9e2da",
        ...sx,
      }}
    >
      <Typography
        variant="caption"
        sx={{
          color: "#888888",
          fontWeight: 700,
        }}
      >
        {label}
      </Typography>

      <Typography
        sx={{
          mt: 0.7,
          color: "#4f2c1a",
          fontWeight: 700,
          lineHeight: 1.7,
          whiteSpace: "pre-wrap",
        }}
      >
        {value}
      </Typography>
    </Paper>
  );
}

function DefinitionStatusChip({
  status,
}: {
  status: string;
}) {
  const styles: Record<
    string,
    {
      label: string;
      background: string;
      color: string;
    }
  > = {
    not_generated: {
      label: "Not Generated",
      background: "#f1f1f1",
      color: "#666666",
    },
    generated: {
      label: "Pending Review",
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
    styles[status] ?? styles.not_generated;

  return (
    <Chip
      label={selected.label}
      sx={{
        bgcolor: selected.background,
        color: selected.color,
        fontWeight: 800,
      }}
    />
  );
}

export default GenerateDefinitionDialog;
