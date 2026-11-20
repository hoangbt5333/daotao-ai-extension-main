/**
 * Helper functions for file management in CourseGeneratorTool
 */

export interface MergeFilesResult {
  merged: File[];
  replacedNames: string[];
  addedNames: string[];
}

/**
 * Pure function to merge incoming files into existing files.
 * If a file with the same name (case-insensitive) already exists,
 * it replaces the old version at the same position.
 * Otherwise, it appends the new file at the end.
 *
 * @param existing Current list of files
 * @param incoming New incoming files
 * @returns Result object containing the new merged array and tracked replaced/added names
 */
export function mergeFiles(existing: File[], incoming: File[]): MergeFilesResult {
  const replacedNames: string[] = [];
  const addedNames: string[] = [];
  const result: File[] = [...existing];

  for (const incomingFile of incoming) {
    const incomingLower = incomingFile.name.toLowerCase();
    const existingIndex = result.findIndex(
      f => f.name.toLowerCase() === incomingLower
    );

    if (existingIndex >= 0) {
      result[existingIndex] = incomingFile;
      if (!replacedNames.includes(incomingFile.name)) {
        replacedNames.push(incomingFile.name);
      }
    } else {
      result.push(incomingFile);
      addedNames.push(incomingFile.name);
    }
  }

  return {
    merged: result,
    replacedNames,
    addedNames,
  };
}

/**
 * Format file size in human-readable format.
 */
export function formatFileSize(bytes: number): string {
  if (bytes <= 0 || isNaN(bytes)) return '0 B';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export interface MissingFileUnit {
  chapterTitle: string;
  subsectionTitle: string;
  unitTitle: string;
  expectedFileName: string;
  type?: string;
}

/**
 * Scan outline for units referencing files that are not present in uploadedFiles.
 * Returns a list of units with their missing file references.
 */
export function getUnitsWithMissingFiles(
  outline: { outline?: Array<{ title?: string; subsections?: Array<{ title?: string; units?: Array<any> }> }> } | null | undefined,
  uploadedFiles: File[]
): MissingFileUnit[] {
  if (!outline || !Array.isArray(outline.outline)) return [];

  const uploadedNameSet = new Set(
    uploadedFiles.map(f => f.name.toLowerCase().trim())
  );

  const missingUnits: MissingFileUnit[] = [];

  for (const chapter of outline.outline) {
    const chapterTitle = chapter.title || "Chương chưa đặt tên";
    for (const subsection of chapter.subsections || []) {
      const subsectionTitle = subsection.title || "Bài học chưa đặt tên";
      for (const unit of subsection.units || []) {
        const unitTitle = unit.title || "Tiết học chưa đặt tên";
        const unitType = unit.type || "text";

        // Determine referenced file name(s) for this unit
        const referencedFiles: string[] = [];

        // Check unit.file
        if (typeof unit.file === 'string' && unit.file.trim()) {
          referencedFiles.push(unit.file.trim());
        } else if (unit.file && typeof unit.file === 'object' && unit.file.name) {
          referencedFiles.push(unit.file.name.trim());
        }

        // Check unit.pdf_file (for video_pdf or pdf)
        if (typeof unit.pdf_file === 'string' && unit.pdf_file.trim()) {
          if (!referencedFiles.includes(unit.pdf_file.trim())) {
            referencedFiles.push(unit.pdf_file.trim());
          }
        }

        // Check unit.audio_file (for audio)
        if (typeof unit.audio_file === 'string' && unit.audio_file.trim()) {
          if (!referencedFiles.includes(unit.audio_file.trim())) {
            referencedFiles.push(unit.audio_file.trim());
          }
        }

        // Check unit.quiz_file (for video_quiz)
        if (typeof unit.quiz_file === 'string' && unit.quiz_file.trim()) {
          if (!referencedFiles.includes(unit.quiz_file.trim())) {
            referencedFiles.push(unit.quiz_file.trim());
          }
        }

        // Check unit.content when type is video_quiz, audio, or pdf and content is a file name
        if (typeof unit.content === 'string' && unit.content.trim()) {
          const contentTrimmed = unit.content.trim();
          const lower = contentTrimmed.toLowerCase();
          if (
            (unitType === 'video_quiz' && lower.endsWith('.txt')) ||
            (unitType === 'audio' && lower.endsWith('.mp3')) ||
            (unitType === 'pdf' && lower.endsWith('.pdf'))
          ) {
            if (!referencedFiles.includes(contentTrimmed)) {
              referencedFiles.push(contentTrimmed);
            }
          }
        }

        for (const fileName of referencedFiles) {
          if (!uploadedNameSet.has(fileName.toLowerCase())) {
            missingUnits.push({
              chapterTitle,
              subsectionTitle,
              unitTitle,
              expectedFileName: fileName,
              type: unitType,
            });
          }
        }
      }
    }
  }

  return missingUnits;
}
