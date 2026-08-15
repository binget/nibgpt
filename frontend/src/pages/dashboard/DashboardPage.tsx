import {
  Alert,
  Box,
  Chip,
  CircularProgress,
  LinearProgress,
  Paper,
  Typography,
} from "@mui/material";

import {
  useEffect,
  useState,
} from "react";

import {
  getExecutiveDashboard,
} from "../../services/executiveDashboard";

import type {
  DomainReadiness,
  ExecutiveDashboard,
} from "../../types/executiveDashboard";


function DashboardPage() {
  const [dashboard, setDashboard] =
    useState<ExecutiveDashboard | null>(
      null
    );

  const [loading, setLoading] =
    useState(true);

  const [errorMessage, setErrorMessage] =
    useState("");

  useEffect(() => {
    const loadDashboard = async () => {
      try {
        const result =
          await getExecutiveDashboard();

        setDashboard(result);
      } catch (error: any) {
        setErrorMessage(
          error?.response?.data?.detail ??
            "Unable to load the executive dashboard."
        );
      } finally {
        setLoading(false);
      }
    };

    loadDashboard();
  }, []);

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
            Preparing executive AI overview...
          </Typography>
        </Box>
      </Box>
    );
  }

  if (errorMessage || !dashboard) {
    return (
      <Alert severity="error">
        {errorMessage ||
          "Executive dashboard data is unavailable."}
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
          Enterprise AI Overview
        </Typography>

        <Typography
          sx={{
            mt: 0.7,
            color: "#777777",
          }}
        >
          Strategic readiness, business coverage
          and governance across NIBGPT.
        </Typography>
      </Box>

      <Paper
        elevation={0}
        sx={{
          p: {
            xs: 3,
            md: 4,
          },
          borderRadius: 4,
          color: "#ffffff",
          overflow: "hidden",
          background:
            "linear-gradient(135deg, #4f2817 0%, #7d4924 55%, #c18b2f 100%)",
          boxShadow:
            "0 20px 45px rgba(84, 45, 21, 0.16)",
        }}
      >
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: {
              xs: "1fr",
              md: "1.2fr 0.8fr",
            },
            gap: 4,
            alignItems: "center",
          }}
        >
          <Box>
            <Typography
              sx={{
                color:
                  "rgba(255,255,255,0.72)",
                fontWeight: 700,
              }}
            >
              ENTERPRISE AI READINESS
            </Typography>

            <Typography
              variant="h1"
              sx={{
                mt: 1,
                fontWeight: 900,
                fontSize: {
                  xs: "3.5rem",
                  md: "5rem",
                },
              }}
            >
              {dashboard.enterprise_readiness}%
            </Typography>

            <Typography
              variant="h5"
              sx={{
                fontWeight: 800,
              }}
            >
              {dashboard.readiness_label}
            </Typography>

            <Typography
              sx={{
                mt: 1.5,
                maxWidth: 640,
                color:
                  "rgba(255,255,255,0.76)",
                lineHeight: 1.8,
              }}
            >
              {dashboard.ai_ready_business_systems} of{" "}
              {
                dashboard.connected_business_systems
              }{" "}
              connected business systems are ready
              or approaching readiness for governed
              AI reporting.
            </Typography>
          </Box>

          <Box>
            <ExecutiveMetric
              label="Knowledge Maturity"
              value={
                dashboard.knowledge_maturity
              }
            />

            <ExecutiveMetric
              label="Governance Compliance"
              value={
                dashboard.governance_compliance
              }
            />
          </Box>
        </Box>
      </Paper>

      <Box
        sx={{
          mt: 2.5,
          display: "grid",
          gridTemplateColumns: {
            xs: "1fr",
            md: "repeat(3, 1fr)",
          },
          gap: 2,
        }}
      >
        <StrategicCard
          label="Business Systems Connected"
          value={
            dashboard.connected_business_systems
          }
          description="Enterprise systems contributing governed knowledge"
          tone="#5b311b"
        />

        <StrategicCard
          label="AI-Ready Business Areas"
          value={
            dashboard.ai_ready_business_systems
          }
          description="Systems ready for reliable AI-assisted reporting"
          tone="#28774b"
        />

        <StrategicCard
          label="Areas Requiring Attention"
          value={
            dashboard.systems_requiring_attention
          }
          description="Business areas requiring further knowledge preparation"
          tone="#b06c18"
        />
      </Box>

      <Box
        sx={{
          mt: 2.5,
          display: "grid",
          gridTemplateColumns: {
            xs: "1fr",
            xl: "1.55fr 0.85fr",
          },
          gap: 2.5,
        }}
      >
        <Paper
          elevation={0}
          sx={{
            p: 3,
            borderRadius: 3,
            border: "1px solid #e9e2da",
          }}
        >
          <Typography
            variant="h6"
            sx={{
              color: "#4f2c1a",
              fontWeight: 900,
            }}
          >
            Business Readiness
          </Typography>

          <Typography
            variant="body2"
            sx={{
              mt: 0.6,
              mb: 2.5,
              color: "#888888",
            }}
          >
            AI maturity across connected business
            systems.
          </Typography>

          <Box
            sx={{
              display: "grid",
              gap: 1.5,
            }}
          >
            {dashboard.domains.map(
              (domain) => (
                <DomainReadinessCard
                  key={domain.data_source_id}
                  domain={domain}
                />
              )
            )}
          </Box>
        </Paper>

        <Paper
          elevation={0}
          sx={{
            p: 3,
            borderRadius: 3,
            border: "1px solid #e9e2da",
          }}
        >
          <Typography
            variant="h6"
            sx={{
              color: "#4f2c1a",
              fontWeight: 900,
            }}
          >
            Executive Highlights
          </Typography>

          <Typography
            variant="body2"
            sx={{
              mt: 0.6,
              mb: 2.5,
              color: "#888888",
            }}
          >
            Current achievements and areas requiring
            leadership attention.
          </Typography>

          <Box
            sx={{
              display: "grid",
              gap: 1.5,
            }}
          >
            {dashboard.highlights.map(
              (highlight, index) => (
                <Alert
                  key={`${highlight.title}-${index}`}
                  severity={
                    highlight.severity
                  }
                  sx={{
                    borderRadius: 2.5,
                    alignItems: "flex-start",
                  }}
                >
                  <Typography
                    sx={{
                      fontWeight: 900,
                    }}
                  >
                    {highlight.title}
                  </Typography>

                  <Typography
                    variant="body2"
                    sx={{
                      mt: 0.5,
                      lineHeight: 1.65,
                    }}
                  >
                    {highlight.message}
                  </Typography>
                </Alert>
              )
            )}
          </Box>
        </Paper>
      </Box>
    </Box>
  );
}


function ExecutiveMetric({
  label,
  value,
}: {
  label: string;
  value: number;
}) {
  return (
    <Box sx={{ mb: 2.5 }}>
      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          gap: 2,
          mb: 0.8,
        }}
      >
        <Typography
          sx={{
            color:
              "rgba(255,255,255,0.76)",
            fontWeight: 700,
          }}
        >
          {label}
        </Typography>

        <Typography
          sx={{
            fontWeight: 900,
          }}
        >
          {value}%
        </Typography>
      </Box>

      <LinearProgress
        variant="determinate"
        value={value}
        sx={{
          height: 8,
          borderRadius: 5,
          bgcolor:
            "rgba(255,255,255,0.18)",
          "& .MuiLinearProgress-bar": {
            bgcolor: "#ffffff",
            borderRadius: 5,
          },
        }}
      />
    </Box>
  );
}


function StrategicCard({
  label,
  value,
  description,
  tone,
}: {
  label: string;
  value: number;
  description: string;
  tone: string;
}) {
  return (
    <Paper
      elevation={0}
      sx={{
        p: 2.7,
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
        variant="h3"
        sx={{
          mt: 1,
          color: tone,
          fontWeight: 900,
        }}
      >
        {value}
      </Typography>

      <Typography
        variant="body2"
        sx={{
          mt: 0.8,
          color: "#888888",
          lineHeight: 1.6,
        }}
      >
        {description}
      </Typography>
    </Paper>
  );
}


function DomainReadinessCard({
  domain,
}: {
  domain: DomainReadiness;
}) {
  const tone =
    domain.readiness_score >= 80
      ? "#28774b"
      : domain.readiness_score >= 60
        ? "#a56b18"
        : "#a83a32";

  return (
    <Paper
      elevation={0}
      sx={{
        p: 2.2,
        borderRadius: 2.5,
        bgcolor: "#faf8f5",
        border: "1px solid #eee6dc",
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
        <Box>
          <Typography
            sx={{
              color: "#4f2c1a",
              fontWeight: 900,
            }}
          >
            {domain.domain_name}
          </Typography>

          <Typography
            variant="caption"
            sx={{ color: "#888888" }}
          >
            {domain.maturity_level}
          </Typography>
        </Box>

        <Chip
          label={domain.status}
          size="small"
          sx={{
            color: tone,
            bgcolor: `${tone}16`,
            fontWeight: 800,
          }}
        />
      </Box>

      <Box
        sx={{
          mt: 1.7,
          display: "flex",
          justifyContent: "space-between",
          gap: 2,
        }}
      >
        <Typography
          variant="body2"
          sx={{ color: "#777777" }}
        >
          AI readiness
        </Typography>

        <Typography
          variant="body2"
          sx={{
            color: tone,
            fontWeight: 900,
          }}
        >
          {domain.readiness_score}%
        </Typography>
      </Box>

      <LinearProgress
        variant="determinate"
        value={domain.readiness_score}
        sx={{
          mt: 0.8,
          height: 8,
          borderRadius: 5,
          "& .MuiLinearProgress-bar": {
            bgcolor: tone,
            borderRadius: 5,
          },
        }}
      />

      {domain.requires_attention &&
        domain.attention_reason && (
          <Typography
            variant="caption"
            sx={{
              display: "block",
              mt: 1.2,
              color: "#9c5c19",
            }}
          >
            {domain.attention_reason}
          </Typography>
        )}
    </Paper>
  );
}

export default DashboardPage;