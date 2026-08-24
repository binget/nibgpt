import {
  AssessmentOutlined,
  DashboardOutlined,
  DescriptionOutlined,
  GroupOutlined,
  HubOutlined,
  PsychologyOutlined,
  SettingsOutlined,
  SmartToyOutlined,
  StorageOutlined,
  AutoAwesomeOutlined,
} from "@mui/icons-material";
import {
  Box,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Typography,
} from "@mui/material";
import { NavLink } from "react-router-dom";

interface MenuItem {
  text: string;
  path: string;
  icon: React.ReactNode;
}

const menuItems: MenuItem[] = [
  {
    text: "Dashboard",
    path: "/dashboard",
    icon: <DashboardOutlined />,
  },
  {
  text: "NIBGPT AI",
  path: "/nibgpt",
  icon: <AutoAwesomeOutlined />,
},
  {
    text: "AI Chat",
    path: "/chat",
    icon: <SmartToyOutlined />,
  },
  {
  text: "Ask NibGPT",
  path: "/ask",
  icon: <SmartToyOutlined />,
},
  {
    text: "Prompt Reports",
    path: "/reports",
    icon: <AssessmentOutlined />,
  },
  {
  text: "Prompt Intelligence",
  path: "/prompt-intelligence",
  icon: (
    <Box
      component="span"
      sx={{
        fontWeight: 900,
        fontSize: "0.75rem",
      }}
    >
      PI
    </Box>
  ),
},
{
  text: "AI Playground",
  path: "/ai-playground",
  icon: (
    <Box
      component="span"
      sx={{
        fontWeight: 900,
        fontSize: "0.75rem",
      }}
    >
      AI
    </Box>
  ),
},
  {
    text: "Documents",
    path: "/documents",
    icon: <DescriptionOutlined />,
  },
  

  {
    text: "Knowledge Base",
    path: "/knowledge-base",
    icon: <PsychologyOutlined />,
  },

  {
    text: "Data Sources",
    path: "/data-sources",
    icon: <StorageOutlined />,
  },
  
  {
  text: "Metadata Explorer",
  path: "/metadata",
  icon: (
    <Box
      component="span"
      sx={{
        fontWeight: 900,
        fontSize: "0.78rem",
      }}
    >
      MD
    </Box>
  ),
},
  

  {
  text: "Business Capabilities",
  path: "/business-capabilities",
  icon: (
    <Box
      component="span"
      sx={{
        fontWeight: 900,
        fontSize: "0.68rem",
      }}
    >
      BC
    </Box>
  ),
},
  {
  text: "Business Entities",
  path: "/business-entities",
  icon: (
    <Box
      component="span"
      sx={{
        fontWeight: 900,
        fontSize: "0.72rem",
      }}
    >
      BE
    </Box>
  ),
},



{
  text: "Relationships",
  path: "/business-relationships",
  icon: (
    <Box
      component="span"
      sx={{
        fontWeight: 900,
        fontSize: "0.7rem",
      }}
    >
      RE
    </Box>
  ),
},
{
  text: "Knowledge Graph",
  path: "/knowledge-graph",
  icon: (
    <Box
      component="span"
      sx={{
        fontWeight: 900,
        fontSize: "0.7rem",
      }}
    >
      KG
    </Box>
  ),
},
{
  text: "Reasoning Explorer",
  path: "/reasoning-explorer",
  icon: (
    <Box
      component="span"
      sx={{
        fontWeight: 900,
        fontSize: "0.68rem",
      }}
    >
      RX
    </Box>
  ),
},

{
  text: "Business Rules",
  path: "/business-rules",
  icon: (
    <Box
      component="span"
      sx={{
        fontWeight: 900,
        fontSize: "0.68rem",
      }}
    >
      SQL
    </Box>
  ),
},

{
  text: "SQL Compiler",
  path: "/sql-compiler",
  icon: (
    <Box
      component="span"
      sx={{
        fontWeight: 900,
        fontSize: "0.68rem",
      }}
    >
      SQL
    </Box>
  ),
},
  {
    text: "AI Models",
    path: "/ai-models",
    icon: <HubOutlined />,
  },
  {
    text: "Users",
    path: "/users",
    icon: <GroupOutlined />,
  },
  {
    text: "Settings",
    path: "/settings",
    icon: <SettingsOutlined />,
  },
];

function Sidebar() {
  return (
    <Box
      component="aside"
      sx={{
        width: 270,
        minWidth: 270,
        minHeight: "100vh",
        bgcolor: "#5b311b",
        color: "#ffffff",
        boxShadow: "6px 0 24px rgba(45, 24, 12, 0.12)",
      }}
    >
      <Box
        sx={{
          px: 3,
          py: 3,
          borderBottom: "1px solid rgba(255,255,255,0.12)",
        }}
      >
        <Typography
          variant="h4"
          sx={{
            fontWeight: 900,
            letterSpacing: "-1px",
          }}
        >
          Nib
          <Box component="span" sx={{ color: "#e0aa39" }}>
            GPT
          </Box>
        </Typography>

        <Typography
          variant="caption"
          sx={{
            display: "block",
            mt: 0.5,
            color: "rgba(255,255,255,0.65)",
          }}
        >
          Enterprise AI Platform
        </Typography>
      </Box>

      <List sx={{ px: 1.5, py: 2 }}>
        {menuItems.map((item) => (
          <ListItemButton
            key={item.path}
            component={NavLink}
            to={item.path}
            sx={{
              mb: 0.6,
              borderRadius: 2,
              color: "rgba(255,255,255,0.82)",
              "& .MuiListItemIcon-root": {
                color: "#d9a438",
                minWidth: 42,
              },
              "&:hover": {
                bgcolor: "rgba(255,255,255,0.09)",
                color: "#ffffff",
              },
              "&.active": {
                bgcolor: "#ffffff",
                color: "#5b311b",
                fontWeight: 700,
                boxShadow: "0 8px 22px rgba(0,0,0,0.18)",
              },
              "&.active .MuiListItemIcon-root": {
                color: "#b77b24",
              },
            }}
          >
            <ListItemIcon>{item.icon}</ListItemIcon>
            <ListItemText
            primary={item.text}
            slotProps={{
              primary: {
                sx: {
                  fontSize: "0.93rem",
                  fontWeight: "inherit",
                },
              },
            }}
          />
          </ListItemButton>
        ))}
      </List>
    </Box>
  );
}

export default Sidebar;