import React, { useState } from "react";
import { 
  Box, 
  Button, 
  IconButton, 
  Dialog, 
  DialogTitle, 
  DialogContent, 
  DialogActions, 
  TextField, 
  Typography, 
  Paper,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  List,
  ListItem,
  ListItemText,
  Divider,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  Stack
} from "@mui/material";
import AddIcon from '@mui/icons-material/Add';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import DownloadIcon from '@mui/icons-material/Download';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import VideoFileIcon from '@mui/icons-material/VideoFile';
import PictureAsPdfIcon from '@mui/icons-material/PictureAsPdf';
import DescriptionIcon from '@mui/icons-material/Description';
import UploadIcon from '@mui/icons-material/Upload';

// Outline data type
interface OutlineUnit {
  title: string;
  type?: 'video' | 'pdf' | 'docx' | 'text' | 'video_pdf';
  file?: File | null;
  fileUrl?: string;
  video_url?: string; // For video and video_pdf types
  pdf_file?: string; // For video_pdf type
}

interface OutlineSubsection {
  title: string;
  units: OutlineUnit[];
}

interface OutlineChapter {
  title: string;
  subsections: OutlineSubsection[];
}

export interface OutlineData {
  outline: OutlineChapter[];
}

// Main component
export default function EditableOutlineTree({
  outlineData,
  onChange
}: {
  outlineData: OutlineData;
  onChange: (data: OutlineData) => void;
}) {
  // Ensure outlineData has the correct structure
  const safeOutlineData = outlineData || { outline: [] };
  const outline = safeOutlineData.outline || [];
  
  // Debug logging
  console.log("EditableOutlineTree received outlineData:", outlineData);
  console.log("Safe outline data:", safeOutlineData);
  console.log("Outline array:", outline);
  
  const [editDialog, setEditDialog] = useState<null | { 
    type: 'chapter'|'subsection'|'unit', 
    chapterIdx?: number, 
    subIdx?: number, 
    unitIdx?: number, 
    value: string, 
    mode: 'edit'|'add',
    unitType?: 'video' | 'pdf' | 'docx' | 'text' | 'video_pdf',
    unitFile?: File | null,
    pdfFile?: File | null,
    videoUrl?: string
  }>(null);

  // Log dữ liệu outline để debug
  console.log('OutlineData:', safeOutlineData);

  // Handlers for edit/add/delete
  const handleEdit = (type: 'chapter'|'subsection'|'unit', idxs: any, value: string) => {
    if (type === 'unit') {
      const { chapterIdx, subIdx, unitIdx } = idxs;
      const unit = safeOutlineData.outline[chapterIdx]?.subsections[subIdx]?.units[unitIdx];
      setEditDialog({ 
        type, 
        ...idxs, 
        value, 
        mode: 'edit',
        unitType: unit?.type || 'text',
        unitFile: unit?.file || null,
        pdfFile: unit?.pdf_file ? new File([], unit.pdf_file) : null,
        videoUrl: unit?.video_url || ''
      });
    } else {
    setEditDialog({ type, ...idxs, value, mode: 'edit' });
    }
  };
  
  const handleAdd = (type: 'chapter'|'subsection'|'unit', idxs: any) => {
    if (type === 'unit') {
      setEditDialog({ type, ...idxs, value: '', mode: 'add', unitType: 'text', unitFile: null });
    } else {
    setEditDialog({ type, ...idxs, value: '', mode: 'add' });
    }
  };
  
  const handleDelete = (type: 'chapter'|'subsection'|'unit', idxs: any) => {
    const newData = JSON.parse(JSON.stringify(safeOutlineData));
    if (type === 'chapter') newData.outline.splice(idxs.chapterIdx, 1);
    if (type === 'subsection') newData.outline[idxs.chapterIdx].subsections.splice(idxs.subIdx, 1);
    if (type === 'unit') newData.outline[idxs.chapterIdx].subsections[idxs.subIdx].units.splice(idxs.unitIdx, 1);
    onChange(newData);
  };
  
  const handleDialogSave = () => {
    if (!editDialog) return;
    const { type, chapterIdx, subIdx, unitIdx, value, mode, unitType, unitFile, pdfFile, videoUrl } = editDialog;
    const newData = JSON.parse(JSON.stringify(safeOutlineData));
    
    if (type === 'chapter') {
      if (mode === 'edit' && chapterIdx !== undefined) newData.outline[chapterIdx].title = value;
      if (mode === 'add') newData.outline.push({ title: value, subsections: [] });
    }
    if (type === 'subsection' && chapterIdx !== undefined) {
      if (mode === 'edit' && subIdx !== undefined) newData.outline[chapterIdx].subsections[subIdx].title = value;
      if (mode === 'add') newData.outline[chapterIdx].subsections.push({ title: value, units: [] });
    }
    if (type === 'unit' && chapterIdx !== undefined && subIdx !== undefined) {
      const unitData: any = { 
        title: value,
        type: unitType || 'text',
        file: unitFile || null
      };
      
      // Add video_url for video and video_pdf types
      if ((unitType === 'video' || unitType === 'video_pdf') && videoUrl) {
        unitData.video_url = videoUrl;
      }
      
      // Add pdf_file for video_pdf type
      if (unitType === 'video_pdf' && pdfFile) {
        unitData.pdf_file = pdfFile.name;
      }
      
      if (mode === 'edit' && unitIdx !== undefined) {
        newData.outline[chapterIdx].subsections[subIdx].units[unitIdx] = {
          ...newData.outline[chapterIdx].subsections[subIdx].units[unitIdx],
          ...unitData
        };
      }
      if (mode === 'add') newData.outline[chapterIdx].subsections[subIdx].units.push(unitData);
    }
    onChange(newData);
    setEditDialog(null);
  };

  const getUnitIcon = (type?: string) => {
    switch (type) {
      case 'video': return <VideoFileIcon fontSize="small" />;
      case 'pdf': return <PictureAsPdfIcon fontSize="small" />;
      case 'docx': return <DescriptionIcon fontSize="small" />;
      case 'video_pdf': return <VideoFileIcon fontSize="small" />;
      default: return null;
    }
  };

  const getUnitTypeLabel = (type?: string) => {
    switch (type) {
      case 'video': return 'Video';
      case 'pdf': return 'PDF';
      case 'docx': return 'DOCX';
      case 'video_pdf': return 'Video + PDF';
      default: return 'Text';
    }
  };

  // Download JSON
  const handleDownload = () => {
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(safeOutlineData, null, 2));
    const a = document.createElement('a');
    a.href = dataStr;
    a.download = 'outline.json';
    a.click();
  };

  return (
    <Paper sx={{ p: 2, mb: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h6" fontWeight={600}>Outline (có thể chỉnh sửa):</Typography>
        <Box>
          <Button 
            variant="outlined" 
            startIcon={<AddIcon />} 
            onClick={() => handleAdd('chapter', {})}
            sx={{ mr: 1 }}
          >
            Thêm Chương
          </Button>
          <Button 
            variant="outlined" 
            startIcon={<DownloadIcon />} 
            onClick={handleDownload}
          >
          Tải về JSON
        </Button>
        </Box>
      </Box>

      {outline.length === 0 ? (
        <Typography color="text.secondary" sx={{ textAlign: 'center', py: 4 }}>
          Chưa có outline để hiển thị. Hãy thêm chương đầu tiên!
        </Typography>
      ) : (
        <Box>
          {outline.map((chapter, cIdx) => (
            <Accordion key={`chapter-${cIdx}`} sx={{ mb: 1 }}>
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Box sx={{ display: 'flex', alignItems: 'center', width: '100%' }}>
                  <Typography fontWeight={600} sx={{ flexGrow: 1 }}>
                    Chương {cIdx + 1}: {chapter.title}
                  </Typography>
                  <IconButton 
                    size="small" 
                    onClick={(e) => {
                      e.stopPropagation();
                      handleEdit('chapter', { chapterIdx: cIdx }, chapter.title);
                    }}
                  >
                    <EditIcon fontSize="small" />
                  </IconButton>
                  <IconButton 
                    size="small" 
                    onClick={(e) => {
                      e.stopPropagation();
                      handleAdd('subsection', { chapterIdx: cIdx });
                    }}
                  >
                    <AddIcon fontSize="small" />
                  </IconButton>
                  <IconButton 
                    size="small" 
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDelete('chapter', { chapterIdx: cIdx });
                    }}
                  >
                    <DeleteIcon fontSize="small" />
                  </IconButton>
                </Box>
              </AccordionSummary>
              <AccordionDetails>
                {chapter.subsections.length === 0 ? (
                  <Typography color="text.secondary" sx={{ textAlign: 'center', py: 2 }}>
                    Chưa có mục nhỏ nào. Hãy thêm mục nhỏ đầu tiên!
                  </Typography>
                ) : (
                  <Box>
                    {chapter.subsections.map((subsection, sIdx) => (
                      <Accordion key={`subsection-${cIdx}-${sIdx}`} sx={{ mb: 1, ml: 2 }}>
                        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                          <Box sx={{ display: 'flex', alignItems: 'center', width: '100%' }}>
                            <Typography sx={{ flexGrow: 1 }}>
                              {subsection.title}
                            </Typography>
                            <IconButton 
                              size="small" 
                              onClick={(e) => {
                                e.stopPropagation();
                                handleEdit('subsection', { chapterIdx: cIdx, subIdx: sIdx }, subsection.title);
                              }}
                            >
                              <EditIcon fontSize="small" />
                            </IconButton>
                            <IconButton 
                              size="small" 
                              onClick={(e) => {
                                e.stopPropagation();
                                handleAdd('unit', { chapterIdx: cIdx, subIdx: sIdx });
                              }}
                            >
                              <AddIcon fontSize="small" />
                            </IconButton>
                            <IconButton 
                              size="small" 
                              onClick={(e) => {
                                e.stopPropagation();
                                handleDelete('subsection', { chapterIdx: cIdx, subIdx: sIdx });
                              }}
                            >
                              <DeleteIcon fontSize="small" />
                            </IconButton>
                          </Box>
                        </AccordionSummary>
                        <AccordionDetails>
                          {subsection.units.length === 0 ? (
                            <Typography color="text.secondary" sx={{ textAlign: 'center', py: 2 }}>
                              Chưa có đơn vị học liệu nào. Hãy thêm đơn vị đầu tiên!
                            </Typography>
                          ) : (
                            <List dense>
                              {subsection.units.map((unit, uIdx) => (
                                <ListItem key={`unit-${cIdx}-${sIdx}-${uIdx}`}>
                                  <Box sx={{ display: 'flex', alignItems: 'center', width: '100%' }}>
                                    {getUnitIcon(unit.type)}
                                    <ListItemText 
                                      primary={
                                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                          <span>{unit.title}</span>
                                          {unit.type && unit.type !== 'text' && (
                                            <Chip 
                                              label={getUnitTypeLabel(unit.type)} 
                                              size="small" 
                                              variant="outlined"
                                              color="primary"
                                            />
                                          )}
                                        </Box>
                                      }
                                      secondary={
                                        unit.video_url && (
                                          <Typography variant="caption" color="text.secondary">
                                            Video URL: {unit.video_url}
                                          </Typography>
                                        )
                                      }
                                    />
                                    <IconButton 
                                      size="small" 
                                      onClick={() => handleEdit('unit', { chapterIdx: cIdx, subIdx: sIdx, unitIdx: uIdx }, unit.title)}
                                    >
                                      <EditIcon fontSize="small" />
                                    </IconButton>
                                    <IconButton 
                                      size="small" 
                                      onClick={() => handleDelete('unit', { chapterIdx: cIdx, subIdx: sIdx, unitIdx: uIdx })}
                                    >
                                      <DeleteIcon fontSize="small" />
                                    </IconButton>
                                  </Box>
                                </ListItem>
                              ))}
                            </List>
                          )}
                        </AccordionDetails>
                      </Accordion>
                    ))}
                  </Box>
                )}
              </AccordionDetails>
            </Accordion>
          ))}
        </Box>
      )}

      {/* Edit Dialog */}
      <Dialog open={!!editDialog} onClose={() => setEditDialog(null)} maxWidth="sm" fullWidth>
        <DialogTitle>
          {editDialog?.mode === 'edit' ? 'Chỉnh sửa' : 'Thêm mới'} {
            editDialog?.type === 'chapter' ? 'Chương' : 
            editDialog?.type === 'subsection' ? 'Mục nhỏ' : 
            'Đơn vị học liệu'
          }
        </DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="Tiêu đề"
            fullWidth
            value={editDialog?.value || ''}
            onChange={e => setEditDialog(editDialog ? { ...editDialog, value: e.target.value } : null)}
            sx={{ mb: 2 }}
          />
          
          {editDialog?.type === 'unit' && (
            <>
              <FormControl fullWidth sx={{ mb: 2 }}>
                <InputLabel>Loại học liệu</InputLabel>
                <Select
                  value={editDialog.unitType || 'text'}
                  label="Loại học liệu"
                  onChange={(e) => setEditDialog(editDialog ? { ...editDialog, unitType: e.target.value as any } : null)}
                >
                  <MenuItem value="text">Text</MenuItem>
                  <MenuItem value="video">Video</MenuItem>
                  <MenuItem value="pdf">PDF</MenuItem>
                  <MenuItem value="docx">DOCX</MenuItem>
                  <MenuItem value="video_pdf">Video + PDF</MenuItem>
                </Select>
              </FormControl>
              
              {(editDialog.unitType === 'video' || editDialog.unitType === 'video_pdf') && (
                <Box sx={{ mb: 2 }}>
                  <Typography variant="subtitle2" sx={{ mb: 1 }}>
                    Đường link video (tùy chọn):
                  </Typography>
                  <TextField
                    fullWidth
                    label="URL Video"
                    placeholder="https://example.com/video.mp4"
                    value={editDialog.videoUrl || ''}
                    onChange={(e) => setEditDialog(editDialog ? { ...editDialog, videoUrl: e.target.value } : null)}
                    helperText="Nhập đường link video từ cloud storage (YouTube, Vimeo, CDN, etc.)"
                    sx={{ mb: 2 }}
                  />
                </Box>
              )}
              
              {(editDialog.unitType === 'pdf' || editDialog.unitType === 'docx') && (
                <Box sx={{ mb: 2 }}>
                  <input
                    type="file"
                    accept={
                      editDialog.unitType === 'pdf' ? '.pdf' :
                      '.docx,.doc'
                    }
                    onChange={(e) => {
                      const file = e.target.files?.[0] || null;
                      setEditDialog(editDialog ? { ...editDialog, unitFile: file } : null);
                    }}
                    style={{ display: 'none' }}
                    id="unit-file-upload"
                  />
                  <label htmlFor="unit-file-upload">
                    <Button
                      variant="outlined"
                      component="span"
                      startIcon={<UploadIcon />}
                      fullWidth
                    >
                      {editDialog.unitFile ? editDialog.unitFile.name : `Chọn file ${editDialog.unitType?.toUpperCase()}`}
                    </Button>
                  </label>
                  {editDialog.unitFile && (
                    <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                      Đã chọn: {editDialog.unitFile.name} ({(editDialog.unitFile.size / 1024 / 1024).toFixed(2)} MB)
                    </Typography>
                  )}
                </Box>
              )}
              
              {editDialog.unitType === 'video_pdf' && (
                <Box sx={{ mb: 2 }}>
                  <Typography variant="subtitle2" sx={{ mb: 1 }}>
                    Tài liệu PDF đi kèm:
                  </Typography>
                  <input
                    type="file"
                    accept=".pdf"
                    onChange={(e) => {
                      const file = e.target.files?.[0] || null;
                      setEditDialog(editDialog ? { ...editDialog, pdfFile: file } : null);
                    }}
                    style={{ display: 'none' }}
                    id="pdf-file-upload"
                  />
                  <label htmlFor="pdf-file-upload">
                    <Button
                      variant="outlined"
                      component="span"
                      startIcon={<UploadIcon />}
                      fullWidth
                    >
                      {editDialog.pdfFile ? editDialog.pdfFile.name : 'Chọn file PDF'}
                    </Button>
                  </label>
                  {editDialog.pdfFile && (
                    <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                      Đã chọn: {editDialog.pdfFile.name} ({(editDialog.pdfFile.size / 1024 / 1024).toFixed(2)} MB)
                    </Typography>
                  )}
                </Box>
              )}
            </>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditDialog(null)}>Hủy</Button>
          <Button onClick={handleDialogSave} variant="contained">Lưu</Button>
        </DialogActions>
      </Dialog>
    </Paper>
  );
} 