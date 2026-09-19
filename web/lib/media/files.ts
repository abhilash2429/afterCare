export type ImageType = "image/jpeg" | "image/png";

export function imageTypeOf(file: File): ImageType | null {
  const type = file.type.toLowerCase();
  const name = file.name.toLowerCase();
  if (type === "image/jpeg" || type === "image/jpg") return "image/jpeg";
  if (type === "image/png") return "image/png";
  if (name.endsWith(".png")) return "image/png";
  if (name.endsWith(".jpg") || name.endsWith(".jpeg")) return "image/jpeg";
  return null;
}

export function sharedImageType(files: File[]): ImageType | null {
  const types = files.map(imageTypeOf);
  if (types.some((type) => type === null)) return null;
  const unique = new Set(types);
  if (unique.size !== 1) return null;
  return types[0] as ImageType;
}
