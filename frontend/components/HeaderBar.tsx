import React from 'react';
import AppBar from '@mui/material/AppBar';
import Toolbar from '@mui/material/Toolbar';
import Typography from '@mui/material/Typography';
import IconButton from '@mui/material/IconButton';
import Link from '@mui/material/Link';
import WbSunnyIcon from '@mui/icons-material/WbSunny';
import DarkModeIcon from '@mui/icons-material/DarkMode';

export default function HeaderBar({ darkMode, onToggleDark }: { darkMode: boolean, onToggleDark: () => void }) {
  return (
    <AppBar position="fixed" sx={{ zIndex: 1201, background: 'linear-gradient(90deg,#1a357a,#2d4d9c)' }}>
      <Toolbar>
        <Typography variant="h6" sx={{ flexGrow: 1, fontWeight: 700, letterSpacing: 1 }}>
          daotao-ai-extension
        </Typography>
        <Link href="https://daotao.ai" color="inherit" underline="none" target="_blank" sx={{ mr: 2, fontWeight: 500 }}>
          daotao.ai
        </Link>
        <IconButton color="inherit" onClick={onToggleDark}>
          {darkMode ? <WbSunnyIcon /> : <DarkModeIcon />}
        </IconButton>
      </Toolbar>
    </AppBar>
  );
} 