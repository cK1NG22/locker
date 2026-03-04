import { useState, useEffect, useCallback } from "react";
import { api } from "../lib/api";

export interface SkillFileMeta {
  id: string;
  path: string;
  size_bytes: number;
  created_at: string;
}

export interface SkillFileFull extends SkillFileMeta {
  content: string;
}

export interface SkillMeta {
  id: string;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
  file_count: number;
}

export interface SkillFull extends SkillMeta {
  content: string;
  files: SkillFileMeta[];
}

export function useSkills() {
  const [skills, setSkills] = useState<SkillMeta[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      setError(null);
      const data = await api.get<{ skills: SkillMeta[] }>("/api/v1/skills");
      setSkills(data.skills);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load skills");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const getSkill = useCallback(async (id: string): Promise<SkillFull> => {
    return api.get<SkillFull>(`/api/v1/skills/${id}`);
  }, []);

  const createSkill = useCallback(
    async (body: { name: string; content: string; description?: string }) => {
      const result = await api.post<{ id: string }>("/api/v1/skills", body);
      await refresh();
      return result;
    },
    [refresh],
  );

  const updateSkill = useCallback(
    async (id: string, body: { name?: string; description?: string }) => {
      await api.put(`/api/v1/skills/${id}`, body);
      await refresh();
    },
    [refresh],
  );

  const deleteSkill = useCallback(
    async (id: string) => {
      await api.delete(`/api/v1/skills/${id}`);
      await refresh();
    },
    [refresh],
  );

  const getSkillFiles = useCallback(
    async (skillId: string): Promise<{ files: SkillFileMeta[] }> => {
      return api.get<{ files: SkillFileMeta[] }>(`/api/v1/skills/${skillId}/files`);
    },
    [],
  );

  const getSkillFile = useCallback(
    async (skillId: string, fileId: string): Promise<SkillFileFull> => {
      return api.get<SkillFileFull>(`/api/v1/skills/${skillId}/files/${fileId}`);
    },
    [],
  );

  const uploadSkillFile = useCallback(
    async (
      skillId: string,
      body: { path: string; content: string },
    ): Promise<SkillFileMeta> => {
      return api.post<SkillFileMeta>(`/api/v1/skills/${skillId}/files`, body);
    },
    [],
  );

  const deleteSkillFile = useCallback(
    async (skillId: string, fileId: string): Promise<void> => {
      await api.delete(`/api/v1/skills/${skillId}/files/${fileId}`);
    },
    [],
  );

  const deployFolder = useCallback(
    async (body: {
      name: string;
      content: string;
      description?: string;
      files: { path: string; content: string }[];
    }) => {
      const result = await api.post<{ id: string }>("/api/v1/skills/deploy-folder", body);
      await refresh();
      return result;
    },
    [refresh],
  );

  return {
    skills,
    loading,
    error,
    refresh,
    getSkill,
    createSkill,
    updateSkill,
    deleteSkill,
    getSkillFiles,
    getSkillFile,
    uploadSkillFile,
    deleteSkillFile,
    deployFolder,
  };
}
