import {
  useEffect,
  useState,
} from "react";

import type {
  FormEvent,
  KeyboardEvent,
} from "react";

import {
  executeNIBGPTQuery,
} from "../../services/queryExecutor";

import type {
  QueryExecutionResponse,
} from "../../types/queryExecutor";

import * as XLSX from "xlsx";

type ResultTab =
  | "data"
  | "sql"
  | "governance";

  type AskMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  result?: QueryExecutionResponse;
  createdAt: string;
};

export default function AskNIBGPTPage() {
  const [prompt, setPrompt] =
    useState("");

  const [loading, setLoading] =
    useState(false);

  const [messages, setMessages] =
  useState<AskMessage[]>([]);

  const processingMessages = [
  "Understanding your question...",
  "Applying business rules...",
  "Finding the right data...",
  "Preparing your report...",
  "Analyzing the results...",
];

const [processingIndex, setProcessingIndex] =
  useState(0);

  const [result, setResult] =
    useState<QueryExecutionResponse | null>(
      null
    );

  const [error, setError] =
    useState<string | null>(null);

  const [activeTab, setActiveTab] =
    useState<ResultTab>("data");

  const [currentPage, setCurrentPage] =
  useState(1);

const [rowsPerPage, setRowsPerPage] =
  useState(10);

  useEffect(() => {
  if (!loading) {
    setProcessingIndex(0);
    return;
  }

  const interval = window.setInterval(
    () => {
      setProcessingIndex(
  (current) => {
    if (
      current >=
      processingMessages.length - 1
    ) {
      return current;
    }

    return current + 1;
  }
);
    },
    1400
  );

  return () => {
    window.clearInterval(
      interval
    );
  };
}, [loading]);

  async function handleSubmit(
    event: FormEvent
  ) {
    event.preventDefault();

    const cleanPrompt =
      prompt.trim();

    if (!cleanPrompt) {
      return;
    }

    const userMessage: AskMessage = {
  id: `user-${Date.now()}`,
  role: "user",
  content: cleanPrompt,
  createdAt: new Date().toISOString(),
};

setMessages((current) => [
  ...current,
  userMessage,
]);

setPrompt("");

    setLoading(true);
    setError(null);
    setActiveTab("data");
    setCurrentPage(1);

    try {
      const response =
        await executeNIBGPTQuery({
          prompt: cleanPrompt,
          requested_limit: 100,
          maximum_entities: 6,
          maximum_path_depth: 4,
          user_role: "analyst",
        });

      setResult(response);

      const assistantMessage: AskMessage = {
  id: `assistant-${Date.now()}`,
  role: "assistant",
  content:
    response.answer ||
    buildAnswer(response),
  result: response,
  createdAt: new Date().toISOString(),
};

setMessages((current) => [
  ...current,
  assistantMessage,
]);

      if (!response.success) {
        setError(
          response.errors?.join(" ") ||
            "NibGPT could not answer this question."
        );
      }
    } catch (err: any) {
      const message =
        err?.response?.data?.detail ||
        err?.message ||
        "Unable to communicate with NibGPT.";

      setError(message);
    } finally {
      setLoading(false);
    }
  }

  function handlePromptKeyDown(
  event: KeyboardEvent<HTMLTextAreaElement>
) {
  if (
    event.key === "Enter" &&
    !event.shiftKey
  ) {
    event.preventDefault();

    if (
      !loading &&
      prompt.trim()
    ) {
      event.currentTarget
        .form
        ?.requestSubmit();
    }
  }
}

function buildAnswer(
  response: QueryExecutionResponse
): string {
  if (
    !response.success ||
    response.rows.length === 0
  ) {
    return "I couldn't find any matching records for this question.";
  }

  const firstRow =
    response.rows[0];

  const columns =
    response.columns;

  // Ranking / aggregation result
  if (
    columns.length >= 2
  ) {
    const firstColumn =
      columns[0];

    const secondColumn =
      columns[1];

    const firstValue =
      firstRow[firstColumn];

    const secondValue =
      firstRow[secondColumn];

    if (
      typeof secondValue ===
      "number"
    ) {
      return (
        `I found ${response.row_count} result` +
        `${response.row_count === 1 ? "" : "s"}. ` +
        `${String(firstValue)} is the leading result ` +
        `with ${formatValue(secondValue)}.`
      );
    }
  }

  return (
    `I found ${response.row_count} matching ` +
    `record${response.row_count === 1 ? "" : "s"} ` +
    `from ${response.data_source_name ?? "the selected data source"}.`
  );
}


function formatValue(
  value: number
): string {
  return new Intl.NumberFormat(
    "en-US",
    {
      maximumFractionDigits: 2,
    }
  ).format(value);
}


const totalRows =
  result?.rows.length ?? 0;

const totalPages = Math.max(
  1,
  Math.ceil(
    totalRows / rowsPerPage
  )
);

const startIndex =
  (currentPage - 1) *
  rowsPerPage;

const paginatedRows =
  result?.rows.slice(
    startIndex,
    startIndex + rowsPerPage
  ) ?? [];

const downloadCSV = (
  report: QueryExecutionResponse,
  reportPrompt: string
) => {
  if (
    !report ||
    !report.success ||
    !report.columns?.length ||
    !report.rows?.length
  ) {
    return;
  }

  const escapeCSVValue = (
    value: unknown
  ) => {
    if (
      value === null ||
      value === undefined
    ) {
      return "";
    }

    const text = String(
      value
    );

    return `"${text.replace(
      /"/g,
      '""'
    )}"`;
  };

  const header = report.columns
    .map(
      (column) =>
        escapeCSVValue(
          column
        )
    )
    .join(",");

  const body = report.rows
    .map((row) =>
      report.columns
        .map(
          (column) =>
            escapeCSVValue(
              row[column]
            )
        )
        .join(",")
    )
    .join("\n");

  const csvContent = [
    header,
    body,
  ].join("\n");

  const blob = new Blob(
    [
      "\uFEFF",
      csvContent,
    ],
    {
      type:
        "text/csv;charset=utf-8;",
    }
  );

  const url =
    URL.createObjectURL(
      blob
    );

  const link =
    document.createElement(
      "a"
    );

  const today =
    new Date()
      .toISOString()
      .slice(
        0,
        10
      );

  const cleanPrompt = reportPrompt
    .trim()
    .replace(
      /[^a-zA-Z0-9\s_-]/g,
      ""
    )
    .replace(
      /\s+/g,
      "_"
    )
    .slice(
      0,
      60
    );

  link.href = url;

  link.download = (
    `NIBGPT_${
      cleanPrompt ||
      "Report"
    }_${today}.csv`
  );

  document.body.appendChild(
    link
  );

  link.click();

  document.body.removeChild(
    link
  );

  URL.revokeObjectURL(
    url
  );
};

const downloadExcel = (
  report: QueryExecutionResponse,
  reportPrompt: string
) => {
  if (
    !report ||
    !report.success ||
    !report.columns?.length ||
    !report.rows?.length
  ) {
    return;
  }

  const worksheetData = report.rows.map(
    (row) => {
      const record: Record<
        string,
        string | number
      > = {};

      report.columns.forEach(
        (column) => {
          const value =
            row[column];

          if (
            typeof value ===
            "number"
          ) {
            record[column] =
              value;
          } else if (
            value === null ||
            value === undefined
          ) {
            record[column] =
              "";
          } else {
            record[column] =
              String(value);
          }
        }
      );

      return record;
    }
  );

  const worksheet =
    XLSX.utils.json_to_sheet(
      worksheetData,
      {
        header:
          report.columns,
      }
    );

  // --------------------------------------------------
  // Auto-size columns
  // --------------------------------------------------

  worksheet["!cols"] =
    report.columns.map(
      (column) => {
        let maxLength =
          column.length;

        report.rows.forEach(
          (row) => {
            const value =
              row[column];

            const text =
              value === null ||
              value === undefined
                ? ""
                : String(
                    value
                  );

            maxLength =
              Math.max(
                maxLength,
                text.length
              );
          }
        );

        return {
          wch: Math.min(
            Math.max(
              maxLength + 2,
              12
            ),
            40
          ),
        };
      }
    );

  // --------------------------------------------------
  // Format numeric cells
  //
  // Count:
  // 1,260,863
  //
  // Balance:
  // 12,540,320.50
  // --------------------------------------------------

  const range =
    XLSX.utils.decode_range(
      worksheet["!ref"] ||
        "A1:A1"
    );

  for (
    let rowIndex =
      range.s.r + 1;
    rowIndex <= range.e.r;
    rowIndex++
  ) {
    for (
      let columnIndex =
        range.s.c;
      columnIndex <=
      range.e.c;
      columnIndex++
    ) {
      const address =
        XLSX.utils.encode_cell(
          {
            r: rowIndex,
            c: columnIndex,
          }
        );

      const cell =
        worksheet[address];

      if (
        !cell ||
        cell.t !== "n"
      ) {
        continue;
      }

      const columnName =
        report.columns[
          columnIndex
        ] || "";

      const normalizedColumn =
        columnName.toLowerCase();

      if (
        normalizedColumn.includes(
          "count"
        )
      ) {
        cell.z = "#,##0";
      } else if (
        normalizedColumn.includes(
          "balance"
        )
        ||
        normalizedColumn.includes(
          "amount"
        )
      ) {
        cell.z =
          "#,##0.00";
      } else {
        cell.z =
          "#,##0.##";
      }
    }
  }

  const workbook =
    XLSX.utils.book_new();

  XLSX.utils.book_append_sheet(
    workbook,
    worksheet,
    "NIBGPT Report"
  );

  const today =
    new Date()
      .toISOString()
      .slice(
        0,
        10
      );

  const cleanPrompt =
    prompt
      .trim()
      .replace(
        /[^a-zA-Z0-9\s_-]/g,
        ""
      )
      .replace(
        /\s+/g,
        "_"
      )
      .slice(
        0,
        60
      );

  const fileName =
    `NIBGPT_${
      cleanPrompt ||
      "Report"
    }_${today}.xlsx`;

  XLSX.writeFile(
    workbook,
    fileName
  );
};

  return (
    <div
      style={{
        maxWidth: "1400px",
        margin: "0 auto",
        padding: "32px",
      }}
    >
      {/* Header */}

      <div
        style={{
          marginBottom: "28px",
        }}
      >
        <h1
          style={{
            margin: 0,
            fontSize: "30px",
            fontWeight: 700,
            color: "#172033",
          }}
        >
          Ask NibGPT
        </h1>

        <p
          style={{
            marginTop: "8px",
            color: "#64748b",
            fontSize: "15px",
          }}
        >
          Ask questions about your business data
          using natural language.
        </p>
      </div>


      {/* Prompt */}

      <form
        onSubmit={handleSubmit}
        style={{
          background: "#ffffff",
          border: "1px solid #e2e8f0",
          borderRadius: "14px",
          padding: "20px",
          boxShadow:
            "0 4px 14px rgba(15, 23, 42, 0.05)",
        }}
      >
        <textarea
          value={prompt}
          onChange={(event) =>
            setPrompt(event.target.value)
          }
          onKeyDown={handlePromptKeyDown}
          placeholder={
            "Ask NibGPT something...\n\n" +
            "Example: Show top 10 vehicles by fuel cost"
          }
          rows={4}
          disabled={loading}
          style={{
            width: "100%",
            resize: "vertical",
            border: "none",
            outline: "none",
            fontSize: "16px",
            lineHeight: 1.6,
            color: "#172033",
            fontFamily: "inherit",
            boxSizing: "border-box",
          }}
        />

        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            borderTop: "1px solid #f1f5f9",
            paddingTop: "16px",
            marginTop: "10px",
          }}
        >
          <span
            style={{
              color: "#94a3b8",
              fontSize: "13px",
            }}
          >
            Enter to ask · Shift + Enter for a new line
          </span>

          <button
            type="submit"
            disabled={
              loading ||
              !prompt.trim()
            }
            style={{
              border: "none",
              borderRadius: "9px",
              padding: "11px 22px",
              background:
                loading || !prompt.trim()
                  ? "#94a3b8"
                  : "#2563eb",
              color: "#ffffff",
              fontWeight: 600,
              cursor:
                loading || !prompt.trim()
                  ? "not-allowed"
                  : "pointer",
            }}
          >
            {loading
              ? "Thinking..."
              : "Ask NibGPT"}
          </button>
        </div>
      </form>

      {loading && (
  <div
    style={{
      marginTop: "18px",
      padding: "18px 20px",
      background:
        "linear-gradient(135deg, #fffaf1, #ffffff)",
      border:
        "1px solid #ead8b7",
      borderRadius: "12px",
      display: "flex",
      alignItems: "center",
      gap: "14px",
      color: "#5b311b",
      boxShadow:
        "0 4px 14px rgba(91,49,27,0.06)",
    }}
  >
    <div
      style={{
        width: "34px",
        height: "34px",
        minWidth: "34px",
        borderRadius: "50%",
        border:
          "3px solid #ead8b7",
        borderTopColor:
          "#b77b24",
        animation:
          "nibgpt-spin 0.8s linear infinite",
      }}
    />

    <div>
      <div
        style={{
          fontWeight: 800,
          fontSize: "14px",
          color: "#5b311b",
        }}
      >
        NIBGPT is working
      </div>

      <div
        style={{
          marginTop: "3px",
          fontSize: "14px",
          color: "#7c5b47",
        }}
      >
        {
          processingMessages[
            processingIndex
          ]
        }
      </div>
    </div>
  </div>
)}


      {/* Error */}

      {error && (
        <div
          style={{
            marginTop: "20px",
            padding: "15px 18px",
            background: "#fef2f2",
            color: "#b91c1c",
            border:
              "1px solid #fecaca",
            borderRadius: "10px",
          }}
        >
          {error}
        </div>
      )}


      {/* Result */}

      {result?.success && (
        <div
          style={{
            marginTop: "14px",
            background: "#ffffff",
            border: "1px solid #e2e8f0",
            borderRadius: "14px",
            overflow: "hidden",
          }}
        >
            <div
  style={{
    marginTop: "26px",
    padding: "22px 24px",
    background:
      "linear-gradient(135deg, #fffaf1, #ffffff)",
    border: "1px solid #ead8b7",
    borderRadius: "14px",
    boxShadow:
      "0 4px 18px rgba(91,49,27,0.06)",
  }}
>
  <div
    style={{
      display: "flex",
      gap: "14px",
      alignItems: "flex-start",
    }}
  >
    <div
      style={{
        width: "38px",
        height: "38px",
        minWidth: "38px",
        borderRadius: "10px",
        display: "grid",
        placeItems: "center",
        background:
          "linear-gradient(135deg, #61351f, #c78f2b)",
        color: "#ffffff",
        fontWeight: 900,
      }}
    >
      N
    </div>

    <div>
      <div
        style={{
          color: "#5b311b",
          fontWeight: 800,
          marginBottom: "6px",
        }}
      >
        NIBGPT
      </div>

      <div
        style={{
          color: "#334155",
          fontSize: "15px",
          whiteSpace: "pre-line",
          lineHeight: 1.7,
        }}
      >
        {result.answer ||
  "NIBGPT completed your request successfully."}
      </div>
    </div>
  </div>
</div>
          {/* Result header */}

          <div
            style={{
              padding: "18px 22px",
              borderBottom:
                "1px solid #e2e8f0",
              display: "flex",
              justifyContent:
                "space-between",
              alignItems: "center",
            }}
          >
            <div>
              <strong
                style={{
                  color: "#172033",
                }}
              >
                Query Result
              </strong>

              <div
                style={{
                  color: "#64748b",
                  fontSize: "13px",
                  marginTop: "4px",
                }}
              >
                {result.data_source_name}
              </div>
            </div>

            <div
  style={{
    display: "flex",
    alignItems: "center",
    gap: "14px",
    flexWrap: "wrap",
  }}
>
  <span
    style={{
      color: "#64748b",
      fontSize: "13px",
    }}
  >
    {result.row_count} rows
  </span>

  <span
    style={{
      color: "#64748b",
      fontSize: "13px",
    }}
  >
    {
      result.execution_time_ms ??
      0
    }{" "}
    ms
  </span>

  <span
    style={{
      color: "#15803d",
      fontWeight: 600,
      fontSize: "13px",
    }}
  >
    {result.decision}
  </span>

  <button
    type="button"
    onClick={() =>
  downloadCSV(
    result,
    prompt
  )
}
    disabled={
      !result.rows?.length
    }
    style={{
      border:
        "1px solid #d6b36a",
      background:
        "linear-gradient(135deg, #fffaf1, #ffffff)",
      color: "#5b311b",
      borderRadius:
        "8px",
      padding:
        "8px 14px",
      fontSize:
        "13px",
      fontWeight:
        700,
      cursor:
        result.rows?.length
          ? "pointer"
          : "not-allowed",
      display:
        "inline-flex",
      alignItems:
        "center",
      gap: "7px",
    }}
  >
    ↓ Download CSV
  </button>

  <button
  type="button"
  onClick={() =>
  downloadExcel(
    result,
    prompt
  )
}
  disabled={
    !result.rows?.length
  }
  style={{
    border:
      "1px solid #15803d",
    background:
      "linear-gradient(135deg, #f0fdf4, #ffffff)",
    color: "#166534",
    borderRadius:
      "8px",
    padding:
      "8px 14px",
    fontSize:
      "13px",
    fontWeight:
      700,
    cursor:
      result.rows?.length
        ? "pointer"
        : "not-allowed",
    display:
      "inline-flex",
    alignItems:
      "center",
    gap: "7px",
  }}
>
  ↓ Download Excel
</button>
</div>
          </div>


          {/* Tabs */}

          <div
            style={{
              display: "flex",
              gap: "4px",
              padding: "10px 18px 0",
              borderBottom:
                "1px solid #e2e8f0",
            }}
          >
            {(
              [
                ["data", "Data"],
                ["sql", "SQL"],
                [
                  "governance",
                  "Governance",
                ],
              ] as const
            ).map(
              ([key, label]) => (
                <button
                  key={key}
                  type="button"
                  onClick={() =>
                    setActiveTab(key)
                  }
                  style={{
                    border: "none",
                    background:
                      "transparent",
                    padding:
                      "10px 14px",
                    cursor: "pointer",
                    color:
                      activeTab === key
                        ? "#2563eb"
                        : "#64748b",
                    fontWeight:
                      activeTab === key
                        ? 600
                        : 500,
                    borderBottom:
                      activeTab === key
                        ? "2px solid #2563eb"
                        : "2px solid transparent",
                  }}
                >
                  {label}
                </button>
              )
            )}
          </div>


          {/* DATA */}

          {activeTab === "data" && (
            <div
              style={{
                overflowX: "auto",
              }}
            >
              <table
                style={{
                  width: "100%",
                  borderCollapse:
                    "collapse",
                }}
              >
                <thead>
                  <tr>
                    {result.columns.map(
                      (column) => (
                        <th
                          key={column}
                          style={{
                            textAlign:
                              "left",
                            padding:
                              "13px 18px",
                            background:
                              "#f8fafc",
                            color:
                              "#475569",
                            fontSize:
                              "13px",
                            borderBottom:
                              "1px solid #e2e8f0",
                          }}
                        >
                          {column}
                        </th>
                      )
                    )}
                  </tr>
                </thead>

                <tbody>
                  {paginatedRows.map(
                    (row, index) => (
                      <tr
                        key={
                          startIndex + index
                        }
                      >
                        {result.columns.map(
                          (column) => (
                            <td
                              key={
                                column
                              }
                              style={{
                                padding:
                                  "13px 18px",
                                borderBottom:
                                  "1px solid #f1f5f9",
                                color:
                                  "#334155",
                                fontSize:
                                  "14px",
                              }}
                            >
                              {typeof row[column] === "number"
  ? row[column].toLocaleString(
      "en-US",
      {
        minimumFractionDigits: 0,
        maximumFractionDigits: 2,
      }
    )
  : String(
      row[column] ?? ""
    )}
                            </td>
                          )
                        )}
                      </tr>
                    )
                  )}
                </tbody>
              </table>
              {result.rows.length > 0 && (
  <div
    style={{
      display: "flex",
      justifyContent:
        "space-between",
      alignItems: "center",
      gap: "16px",
      padding: "14px 18px",
      borderTop:
        "1px solid #e2e8f0",
      background: "#ffffff",
      flexWrap: "wrap",
    }}
  >
    <div
      style={{
        color: "#64748b",
        fontSize: "13px",
      }}
    >
      Showing{" "}
      <strong>
        {startIndex + 1}
      </strong>
      {" - "}
      <strong>
        {Math.min(
          startIndex +
            rowsPerPage,
          result.rows.length
        )}
      </strong>
      {" of "}
      <strong>
        {result.rows.length}
      </strong>
      {" results"}
    </div>

    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: "10px",
      }}
    >
      <select
        value={rowsPerPage}
        onChange={(event) => {
          setRowsPerPage(
            Number(
              event.target.value
            )
          );

          setCurrentPage(1);
        }}
        style={{
          padding: "7px 10px",
          border:
            "1px solid #cbd5e1",
          borderRadius: "7px",
          color: "#475569",
          background: "#ffffff",
        }}
      >
        <option value={10}>
          10 rows
        </option>

        <option value={25}>
          25 rows
        </option>

        <option value={50}>
          50 rows
        </option>

        <option value={100}>
          100 rows
        </option>
      </select>

      <button
        type="button"
        disabled={
          currentPage <= 1
        }
        onClick={() =>
          setCurrentPage(
            (page) =>
              Math.max(
                1,
                page - 1
              )
          )
        }
        style={{
          padding: "7px 13px",
          border:
            "1px solid #cbd5e1",
          borderRadius: "7px",
          background:
            currentPage <= 1
              ? "#f1f5f9"
              : "#ffffff",
          color:
            currentPage <= 1
              ? "#94a3b8"
              : "#334155",
          cursor:
            currentPage <= 1
              ? "not-allowed"
              : "pointer",
        }}
      >
        Previous
      </button>

      <span
        style={{
          color: "#475569",
          fontSize: "13px",
          fontWeight: 600,
        }}
      >
        Page {currentPage} of{" "}
        {totalPages}
      </span>

      <button
        type="button"
        disabled={
          currentPage >=
          totalPages
        }
        onClick={() =>
          setCurrentPage(
            (page) =>
              Math.min(
                totalPages,
                page + 1
              )
          )
        }
        style={{
          padding: "7px 13px",
          border:
            "1px solid #cbd5e1",
          borderRadius: "7px",
          background:
            currentPage >=
            totalPages
              ? "#f1f5f9"
              : "#ffffff",
          color:
            currentPage >=
            totalPages
              ? "#94a3b8"
              : "#334155",
          cursor:
            currentPage >=
            totalPages
              ? "not-allowed"
              : "pointer",
        }}
      >
        Next
      </button>
    </div>
  </div>
)}
            </div>
          )}


          {/* SQL */}

          {activeTab === "sql" && (
            <div
              style={{
                padding: "20px",
              }}
            >
              <pre
                style={{
                  margin: 0,
                  padding: "18px",
                  overflowX: "auto",
                  background: "#0f172a",
                  color: "#e2e8f0",
                  borderRadius: "10px",
                  fontSize: "13px",
                  lineHeight: 1.6,
                }}
              >
                {result.sql}
              </pre>
            </div>
          )}


          {/* Governance */}

          {activeTab ===
            "governance" && (
            <div
              style={{
                padding: "22px",
              }}
            >
              <div
                style={{
                  marginBottom: "18px",
                }}
              >
                <strong>
                  Decision:
                </strong>{" "}
                <span
                  style={{
                    color: "#15803d",
                    fontWeight: 600,
                  }}
                >
                  {result.decision}
                </span>
              </div>

              {result.explanation.map(
                (item, index) => (
                  <div
                    key={index}
                    style={{
                      padding:
                        "10px 0",
                      borderBottom:
                        "1px solid #f1f5f9",
                      color:
                        "#475569",
                      fontSize:
                        "14px",
                    }}
                  >
                    {item}
                  </div>
                )
              )}
            </div>
          )}
        </div>
      )}

      <style>
  {`
    @keyframes nibgpt-spin {
      from {
        transform: rotate(0deg);
      }

      to {
        transform: rotate(360deg);
      }
    }
  `}
</style>
    </div>
  );
}