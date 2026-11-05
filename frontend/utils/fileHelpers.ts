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
