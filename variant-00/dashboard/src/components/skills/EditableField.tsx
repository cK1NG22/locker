import { useState } from "react";

interface EditableFieldProps {
  value: string;
  placeholder?: string;
  onSave: (value: string) => Promise<void>;
  displayClassName?: string;
  inputClassName?: string;
  as?: "h2" | "p";
}

export default function EditableField({
  value,
  placeholder,
  onSave,
  displayClassName = "",
  inputClassName = "",
  as: Tag = "p",
}: EditableFieldProps) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(value);
  const [saving, setSaving] = useState(false);

  const save = async () => {
    if (!draft.trim() || draft === value) {
      setEditing(false);
      setDraft(value);
      return;
    }
    setSaving(true);
    try {
      await onSave(draft.trim());
      setEditing(false);
    } catch (e) {
      alert(e instanceof Error ? e.message : "Save failed");
    } finally {
      setSaving(false);
    }
  };

  const cancel = () => {
    setEditing(false);
    setDraft(value);
  };

  if (editing) {
    return (
      <div className="flex items-center gap-2">
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          className={inputClassName}
          autoFocus
          onKeyDown={(e) => {
            if (e.key === "Enter") save();
            if (e.key === "Escape") cancel();
          }}
        />
        <button onClick={save} disabled={saving} className="text-sm text-blue-600 hover:underline">
          Save
        </button>
        <button onClick={cancel} className="text-sm text-gray-400 hover:underline">
          Cancel
        </button>
      </div>
    );
  }

  return (
    <Tag
      className={`cursor-pointer hover:text-blue-600 transition-colors ${displayClassName}`}
      onClick={() => setEditing(true)}
      title="Click to edit"
    >
      {value || placeholder || ""}
    </Tag>
  );
}
