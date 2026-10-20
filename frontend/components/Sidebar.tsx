import React from 'react';
import Drawer from '@mui/material/Drawer';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import ListItemButton from '@mui/material/ListItemButton';
import ListItemIcon from '@mui/material/ListItemIcon';
import ListItemText from '@mui/material/ListItemText';
import SchoolIcon from '@mui/icons-material/School';
import QuizIcon from '@mui/icons-material/Quiz';
import AssignmentIcon from '@mui/icons-material/Assignment';
import VideoLibraryIcon from '@mui/icons-material/VideoLibrary';
import SwapHorizIcon from '@mui/icons-material/SwapHoriz';
import HelpIcon from '@mui/icons-material/Help';

const usecases = [
  { key: 'create-outline', label: 'Tạo khóa học', icon: <SchoolIcon /> },
  { key: 'question-bank', label: 'Ngân hàng câu hỏi', icon: <QuizIcon /> },
  { key: 'exam-generator', label: 'Tạo đề thi', icon: <AssignmentIcon /> },
  { key: 'video-quiz', label: 'Video Quiz', icon: <VideoLibraryIcon /> },
  { key: 'format-converter', label: 'Chuyển đổi định dạng', icon: <SwapHorizIcon /> },
  { key: 'guide', label: 'Hướng dẫn', icon: <HelpIcon /> },
];

export default function Sidebar({ selected, onSelect }: { selected: string, onSelect: (key: string) => void }) {
  return (
    <Drawer
      variant="permanent"
      sx={{
        width: 220,
        flexShrink: 0,
        [`& .MuiDrawer-paper`]: { width: 220, boxSizing: 'border-box', background: 'linear-gradient(180deg,#1a357a,#2d4d9c)', color: '#fff' },
      }}
    >
      <List>
        {usecases.map((item) => (
          <ListItem key={item.key} disablePadding>
            <ListItemButton selected={selected === item.key} onClick={() => onSelect(item.key)}>
              <ListItemIcon sx={{ color: '#fff' }}>{item.icon}</ListItemIcon>
              <ListItemText primary={item.label} />
            </ListItemButton>
          </ListItem>
        ))}
      </List>
    </Drawer>
  );
} 