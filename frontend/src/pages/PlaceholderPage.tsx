import { ConstructionOutlined } from "@mui/icons-material";
import { Box, Paper, Typography } from "@mui/material";

interface PlaceholderPageProps {
  title: string;
  description: string;
}

function PlaceholderPage({
  title,
  description,
}: PlaceholderPageProps) {
  return (
    <Paper
      elevation={0}
      sx={{
        p: 5,
        borderRadius: 3,
        border: "1px solid #e9e2da",
        textAlign: "center",
      }}
    >
      <Box
        sx={{
          width: 78,
          height: 78,
          mx: "auto",
          mb: 2,
          display: "grid",
          placeItems: "center",
          borderRadius: 3,
          bgcolor: "#fff4dc",
          color: "#a06d1f",
        }}
      >
        <ConstructionOutlined sx={{ fontSize: 42 }} />
      </Box>

      <Typography
        variant="h4"
        sx={{
          color: "#4f2c1a",
          fontWeight: 800,
        }}
      >
        {title}
      </Typography>

      <Typography
        sx={{
          mt: 1.5,
          color: "#777777",
        }}
      >
        {description}
      </Typography>
    </Paper>
  );
}

export default PlaceholderPage;
