import { useCallback, useState } from "react";

interface Props {
  onUpload: (files: File[]) => void;
  loading: boolean;
}

export function ImageUploader({ onUpload, loading }: Props) {
  const [files, setFiles] = useState<File[]>([]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    const dropped = Array.from(e.dataTransfer.files).filter((f) =>
      f.type.startsWith("image/")
    );
    setFiles((prev) => [...prev, ...dropped].slice(0, 10));
  }, []);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const selected = Array.from(e.target.files);
      setFiles((prev) => [...prev, ...selected].slice(0, 10));
    }
  };

  const handleSubmit = () => {
    if (files.length > 0) {
      onUpload(files);
    }
  };

  const removeFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  return (
    <div>
      <div
        onDrop={handleDrop}
        onDragOver={(e) => e.preventDefault()}
        className="border-2 border-dashed border-blue-400 rounded-lg p-8 text-center cursor-pointer hover:bg-blue-50 transition"
        onClick={() => document.getElementById("file-input")?.click()}
      >
        <p className="text-blue-600 font-medium">Drag & drop screenshots here</p>
        <p className="text-gray-400 text-sm mt-1">JPG / PNG, max 10 images</p>
        <input
          id="file-input"
          type="file"
          accept="image/*"
          multiple
          onChange={handleFileChange}
          className="hidden"
        />
      </div>

      {files.length > 0 && (
        <div className="mt-4">
          <div className="flex gap-2 flex-wrap">
            {files.map((file, i) => (
              <div key={i} className="relative w-16 h-16">
                <img
                  src={URL.createObjectURL(file)}
                  alt={file.name}
                  className="w-16 h-16 object-cover rounded border"
                />
                <button
                  onClick={() => removeFile(i)}
                  className="absolute -top-1 -right-1 bg-red-500 text-white rounded-full w-4 h-4 text-xs leading-none"
                >
                  x
                </button>
              </div>
            ))}
          </div>
          <button
            onClick={handleSubmit}
            disabled={loading}
            className="mt-3 w-full bg-blue-600 text-white py-2 rounded-lg font-medium hover:bg-blue-700 disabled:bg-gray-400"
          >
            {loading ? "Extracting..." : "AI Extract Places"}
          </button>
        </div>
      )}
    </div>
  );
}
