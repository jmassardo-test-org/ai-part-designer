export * from './auth';
export * from './job';
// Note: file.ts has a duplicate GeometryInfo, so we explicitly re-export only unique types
export { 
  type FileStatus,
  type CadFormat,
  type FileInfo,
  type DesignFile,
  type DesignVersion,
  type VersionListResponse,
  type VersionComparison,
  type VersionDiffItem,
  type VersionDiff,
} from './file';
