import { ReactNode } from "react";
import { Box, Paper, Typography } from "@mui/material";

interface DashboardCardProps {
  title: string;
  value: string | number;
  description: string;
  icon: ReactNode;
}

function DashboardCard({
  title,
  value,
  description,
  icon,
}: DashboardCardProps) {
  return (
    <Paper
      elevation={0}
      sx={{
        height: "100%",
        p: 2.5,
        borderRadius: 3,
        border: "1px solid #e9e2da",
        transition: "transform 0.2s ease, box-shadow 0.2s ease",
        "&:hover": {
          transform: "translateY(-3px)",
          boxShadow: "0 12px 30px rgba(84, 49, 27, 0.10)",
        },
      }}
    >
      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
        }}
      >
        <Box>
          <Typography
            variant="body2"
            sx={{
              color: "#777777",
              fontWeight: 600,
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
        </Box>

        <Box
          sx={{
            width: 52,
            height: 52,
            borderRadius: 2.5,
            display: "grid",
            placeItems: "center",
            color: "#ffffff",
            background:
              "linear-gradient(145deg, #6a3b21, #d3a034)",
          }}
        >
          {icon}
        </Box>
      </Box>

      <Typography
        variant="caption"
        sx={{
          display: "block",
          mt: 1.5,
          color: "#999999",
        }}
      >
        {description}
      </Typography>
    </Paper>
  );
}

export default DashboardCard;
