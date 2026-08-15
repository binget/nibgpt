import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  AppBar,
  Avatar,
  Box,
  Divider,
  IconButton,
  ListItemIcon,
  Menu,
  MenuItem,
  Toolbar,
  Tooltip,
  Typography,
} from "@mui/material";
import {
  Logout,
  NotificationsNone,
AccountCircle,
} from "@mui/icons-material";



function Topbar() {
  const navigate = useNavigate();

  const [anchorElement, setAnchorElement] =
    useState<null | HTMLElement>(null);

  const menuOpen = Boolean(anchorElement);

  const handleLogout = () => {
    localStorage.removeItem("nibgpt_access_token");
    navigate("/login");
  };

  return (
    <AppBar
      position="sticky"
      elevation={0}
      sx={{
        bgcolor: "rgba(255,255,255,0.96)",
        color: "#263238",
        borderBottom: "1px solid #e8e3dc",
        backdropFilter: "blur(10px)",
      }}
    >
      <Toolbar sx={{ minHeight: "72px !important", px: 3 }}>
        <Box sx={{ flexGrow: 1 }}>
          <Typography
            variant="h6"
            sx={{
              fontWeight: 800,
              color: "#4f2c1a",
            }}
          >
            NibGPT Workspace
          </Typography>

          <Typography variant="caption" sx={{ color: "#7b7b7b" }}>
            Secure internal artificial intelligence environment
          </Typography>
        </Box>

        <Tooltip title="Notifications">
          <IconButton sx={{ mr: 1 }}>
            <NotificationsNone />
          </IconButton>
        </Tooltip>

        <Tooltip title="Administrator account">
          <IconButton
            onClick={(event) => setAnchorElement(event.currentTarget)}
          >
            <Avatar
              sx={{
                width: 40,
                height: 40,
                bgcolor: "#d19a2b",
                color: "#ffffff",
                fontWeight: 800,
              }}
            >
              A
            </Avatar>
          </IconButton>
        </Tooltip>

        <Menu
          anchorEl={anchorElement}
          open={menuOpen}
          onClose={() => setAnchorElement(null)}
          PaperProps={{
            sx: {
              width: 220,
              mt: 1,
              borderRadius: 2,
            },
          }}
        >
          <Box sx={{ px: 2, py: 1.2 }}>
            <Typography sx={{ fontWeight: 700 }}>
              Administrator
            </Typography>
            <Typography variant="caption" sx={{ color: "#777777" }}>
              admin@nibbank.com
            </Typography>
          </Box>

          <Divider />

          <MenuItem>
            <ListItemIcon>
              <AccountCircle fontSize="small" />
            </ListItemIcon>
            My Profile
          </MenuItem>

          <MenuItem onClick={handleLogout}>
            <ListItemIcon>
              <Logout fontSize="small" />
            </ListItemIcon>
            Sign Out
          </MenuItem>
        </Menu>
      </Toolbar>
    </AppBar>
  );
}

export default Topbar;