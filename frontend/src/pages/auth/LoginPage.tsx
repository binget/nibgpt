import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  Container,
  InputAdornment,
  Paper,
  TextField,
  Typography,
} from "@mui/material";
import {
  AccountCircle,
  Lock,
  SmartToyOutlined,
} from "@mui/icons-material";

import api from "../../services/api";

interface LoginResponse {
  access_token: string;
  token_type: string;
}

function LoginPage() {
  const navigate = useNavigate();

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setErrorMessage("");

    if (!username.trim() || !password) {
      setErrorMessage("Please enter your username and password.");
      return;
    }

    try {
      setIsSubmitting(true);

      const response = await api.post<LoginResponse>("/api/auth/login", {
        username: username.trim(),
        password,
      });

      localStorage.setItem(
        "nibgpt_access_token",
        response.data.access_token
      );

      navigate("/dashboard");
    } catch (error: any) {
      const detail = error?.response?.data?.detail;

      setErrorMessage(
        typeof detail === "string"
          ? detail
          : "Unable to sign in. Please check your details."
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Box
      sx={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        background:
          "linear-gradient(135deg, #fffdf8 0%, #f6efe2 50%, #ffffff 100%)",
        position: "relative",
        overflow: "hidden",
      }}
    >
      <Box
        sx={{
          position: "absolute",
          width: 420,
          height: 420,
          borderRadius: "50%",
          background:
            "radial-gradient(circle, rgba(212,162,61,0.22), transparent 70%)",
          top: -120,
          right: -80,
        }}
      />

      <Box
        sx={{
          position: "absolute",
          width: 320,
          height: 320,
          borderRadius: "50%",
          background:
            "radial-gradient(circle, rgba(91,49,27,0.14), transparent 70%)",
          bottom: -100,
          left: -80,
        }}
      />

      <Container maxWidth="sm">
        <Paper
          elevation={14}
          sx={{
            position: "relative",
            borderRadius: 5,
            px: { xs: 3, sm: 6 },
            py: { xs: 4, sm: 6 },
            border: "1px solid rgba(91,49,27,0.10)",
            backdropFilter: "blur(12px)",
            backgroundColor: "rgba(255,255,255,0.94)",
          }}
        >
          <Box sx={{ textAlign: "center", mb: 4 }}>
            <Box
              sx={{
                width: 78,
                height: 78,
                margin: "0 auto 18px",
                borderRadius: "24px",
                display: "grid",
                placeItems: "center",
                background:
                  "linear-gradient(145deg, #6d3c22, #d5a333)",
                boxShadow: "0 12px 30px rgba(109,60,34,0.28)",
              }}
            >
              <SmartToyOutlined sx={{ fontSize: 43, color: "#ffffff" }} />
            </Box>

            <Typography
              variant="h3"
              sx={{
                fontWeight: 800,
                letterSpacing: "-1px",
                color: "#5b311b",
              }}
            >
              Nib
              <Box component="span" sx={{ color: "#d29d2c" }}>
                GPT
              </Box>
            </Typography>

            <Typography
              variant="subtitle1"
              sx={{ color: "#6f6f6f", mt: 1 }}
            >
              Enterprise Artificial Intelligence Platform
            </Typography>

            <Typography
              variant="body2"
              sx={{ color: "#999999", mt: 0.5 }}
            >
              Nib International Bank Sc
            </Typography>
          </Box>

          {errorMessage && (
            <Alert severity="error" sx={{ mb: 2.5 }}>
              {errorMessage}
            </Alert>
          )}

          <Box component="form" onSubmit={handleSubmit}>
            <TextField
              fullWidth
              label="Username or email"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              disabled={isSubmitting}
              autoComplete="username"
              margin="normal"
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <AccountCircle sx={{ color: "#8a5a35" }} />
                  </InputAdornment>
                ),
              }}
            />

            <TextField
              fullWidth
              label="Password"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              disabled={isSubmitting}
              autoComplete="current-password"
              margin="normal"
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <Lock sx={{ color: "#8a5a35" }} />
                  </InputAdornment>
                ),
              }}
            />

            <Button
              fullWidth
              type="submit"
              variant="contained"
              disabled={isSubmitting}
              sx={{
                mt: 3,
                py: 1.4,
                borderRadius: 2.5,
                textTransform: "none",
                fontSize: "1rem",
                fontWeight: 700,
                background:
                  "linear-gradient(90deg, #63371f, #b7782a, #d5a333)",
                boxShadow: "0 10px 22px rgba(126,76,32,0.24)",
                "&:hover": {
                  background:
                    "linear-gradient(90deg, #542d19, #9c6424, #bd8a26)",
                },
              }}
            >
              {isSubmitting ? (
                <CircularProgress size={24} color="inherit" />
              ) : (
                "Sign in to NIBGPT"
              )}
            </Button>
          </Box>

          <Typography
            variant="caption"
            display="block"
            textAlign="center"
            sx={{ color: "#8c8c8c", mt: 4 }}
          >
            Authorized NIB users only. All activities are monitored and
            recorded.
          </Typography>
        </Paper>
      </Container>
    </Box>
  );
}

export default LoginPage;
