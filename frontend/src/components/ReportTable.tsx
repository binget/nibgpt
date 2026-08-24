import {
  Box,
  Button,
  Chip,
  Paper,
  Typography,
} from "@mui/material";

import {
  useState,
} from "react";

import type {
  OrchestratorReport,
} from "../services/orchestrator";


interface ReportTableProps {
  report: OrchestratorReport;
}


function formatCellValue(
  value: unknown
): string {
  if (
    value === null ||
    value === undefined
  ) {
    return "";
  }

  if (typeof value === "number") {
    return value.toLocaleString(
      "en-US",
      {
        maximumFractionDigits: 2,
      }
    );
  }

  return String(value);
}


export default function ReportTable({
  report,
}: ReportTableProps) {
  const rowsPerPage = 10;

  const [page, setPage] =
    useState(1);

  const totalPages =
    Math.max(
      1,
      Math.ceil(
        report.rows.length /
        rowsPerPage
      )
    );

  const startIndex =
    (page - 1) *
    rowsPerPage;

  const endIndex =
    Math.min(
      startIndex +
      rowsPerPage,
      report.rows.length
    );

  const paginatedRows =
    report.rows.slice(
      startIndex,
      endIndex
    );

  const previousPage = () => {
    setPage(
      (current) =>
        Math.max(
          1,
          current - 1
        )
    );
  };


  const nextPage = () => {
    setPage(
      (current) =>
        Math.min(
          totalPages,
          current + 1
        )
    );
  };


  return (
    <Paper
      elevation={0}
      sx={{
        mt: 2,
        border:
          "1px solid #e5ddd7",
        borderRadius: 2.5,
        overflow: "hidden",
      }}
    >
      <Box
        sx={{
          px: 2,
          py: 1.5,
          display: "flex",
          justifyContent:
            "space-between",
          alignItems: "center",
          gap: 2,
          flexWrap: "wrap",
          bgcolor: "#fffaf6",
        }}
      >
        <Box>
          <Typography
            variant="body2"
            sx={{
              fontWeight: 800,
              color: "#4b3021",
            }}
          >
            Report
          </Typography>

          <Typography
            variant="caption"
            sx={{
              color: "#8b7669",
            }}
          >
            {report.row_count} results
          </Typography>
        </Box>

        <Chip
          size="small"
          label={
            report.decision
          }
          sx={{
            bgcolor: "#ecfdf5",
            color: "#047857",
            fontWeight: 700,
          }}
        />
      </Box>

      <Box
        sx={{
          overflowX: "auto",
        }}
      >
        <Box
          component="table"
          sx={{
            width: "100%",
            borderCollapse:
              "collapse",
          }}
        >
          <Box
            component="thead"
          >
            <Box
              component="tr"
            >
              {report.columns.map(
                (column) => (
                  <Box
                    component="th"
                    key={column}
                    sx={{
                      textAlign:
                        "left",
                      px: 2,
                      py: 1.3,
                      bgcolor:
                        "#f8fafc",
                      color:
                        "#64748b",
                      fontSize:
                        "0.75rem",
                      whiteSpace:
                        "nowrap",
                      borderBottom:
                        (
                          "1px solid " +
                          "#e2e8f0"
                        ),
                    }}
                  >
                    {column}
                  </Box>
                )
              )}
            </Box>
          </Box>

          <Box
            component="tbody"
          >
            {paginatedRows.map(
              (
                row,
                index
              ) => (
                <Box
                  component="tr"
                  key={
                    `${startIndex}-${index}`
                  }
                >
                  {report.columns.map(
                    (column) => (
                      <Box
                        component="td"
                        key={column}
                        sx={{
                          px: 2,
                          py: 1.2,
                          color:
                            "#475569",
                          fontSize:
                            "0.8rem",
                          whiteSpace:
                            "nowrap",
                          borderBottom:
                            (
                              "1px solid " +
                              "#f1f5f9"
                            ),
                        }}
                      >
                        {formatCellValue(
                          row[column]
                        )}
                      </Box>
                    )
                  )}
                </Box>
              )
            )}
          </Box>
        </Box>
      </Box>

      <Box
        sx={{
          px: 2,
          py: 1.25,
          borderTop:
            "1px solid #eee",
          bgcolor: "#fafafa",
          display: "flex",
          justifyContent:
            "space-between",
          alignItems: "center",
          gap: 2,
          flexWrap: "wrap",
        }}
      >
        <Typography
          variant="caption"
          sx={{
            color: "#8b7669",
          }}
        >
          Showing{" "}
          {report.rows.length === 0
            ? 0
            : startIndex + 1}
          {" - "}
          {endIndex}
          {" of "}
          {report.rows.length}
        </Typography>

        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            gap: 1,
          }}
        >
          <Button
            size="small"
            disabled={
              page <= 1
            }
            onClick={
              previousPage
            }
            sx={{
              textTransform:
                "none",
              color: "#5b311b",
            }}
          >
            Previous
          </Button>

          <Typography
            variant="caption"
            sx={{
              minWidth: 80,
              textAlign: "center",
              color: "#6f5b4e",
              fontWeight: 700,
            }}
          >
            Page {page} of{" "}
            {totalPages}
          </Typography>

          <Button
            size="small"
            disabled={
              page >=
              totalPages
            }
            onClick={
              nextPage
            }
            sx={{
              textTransform:
                "none",
              color: "#5b311b",
            }}
          >
            Next
          </Button>
        </Box>
      </Box>
    </Paper>
  );
}