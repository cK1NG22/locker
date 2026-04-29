"use client";

import { useState } from "react";
import Link from "next/link";
import { useOrgs } from "@/hooks/useOrgs";

export default function OrgList() {
  const { orgs, loading, error, createOrg, deleteOrg } = useOrgs();
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [creating, setCreating] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const handleCreate = async () => {
    if (!name.trim() || !slug.trim()) return;
    setCreating(true); setFormError(null);
    try { await createOrg(name.trim(), slug.trim()); setName(""); setSlug(""); setShowForm(false); }
    catch (e) { setFormError(e instanceof Error ? e.message : "Create failed"); }
    finally { setCreating(false); }
  };

  const handleDelete = async (id: string, orgName: string) => {
    if (!confirm(`Delete org "${orgName}"? All team links will be removed.`)) return;
    try { await deleteOrg(id); } catch (e) { alert(e instanceof Error ? e.message : "Delete failed"); }
  };

  if (loading) return <p className="text-sm text-gray-500">Loading organizations...</p>;
  if (error) return <p className="text-sm text-red-600">{error}</p>;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-lg font-semibold text-gray-900">Organizations</h2>
        <button onClick={() => setShowForm(!showForm)} className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 transition-colors">Create org</button>
      </div>
      {showForm && (
        <div className="mb-6 p-4 bg-white border border-gray-200 rounded-lg space-y-3">
          <input type="text" placeholder="Organization name" value={name} onChange={(e) => setName(e.target.value)} className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
          <input type="text" placeholder="Slug (e.g. acme-corp)" value={slug} onChange={(e) => setSlug(e.target.value)} className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
          {formError && <p className="text-xs text-red-600">{formError}</p>}
          <button onClick={handleCreate} disabled={creating || !name.trim() || !slug.trim()} className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 disabled:opacity-50 transition-colors">{creating ? "Creating..." : "Create"}</button>
        </div>
      )}
      {orgs.length === 0 ? (
        <p className="text-sm text-gray-500 py-8 text-center">No organizations yet. Create one to group teams together.</p>
      ) : (
        <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead><tr className="border-b border-gray-200 bg-gray-50"><th className="text-left px-4 py-3 font-medium text-gray-600">Name</th><th className="text-left px-4 py-3 font-medium text-gray-600">Slug</th><th className="text-left px-4 py-3 font-medium text-gray-600">Convention</th><th className="w-20 px-4 py-3"></th></tr></thead>
            <tbody>
              {orgs.map((org) => (
                <tr key={org.id} className="border-b border-gray-100 last:border-0 hover:bg-gray-50">
                  <td className="px-4 py-3"><Link href={`/dashboard/orgs/${org.id}`} className="text-blue-600 hover:underline font-medium">{org.name}</Link></td>
                  <td className="px-4 py-3 text-gray-500 font-mono text-xs">{org.slug}</td>
                  <td className="px-4 py-3 text-gray-500 font-mono text-xs">{org.skill_convention}</td>
                  <td className="px-4 py-3"><button onClick={() => handleDelete(org.id, org.name)} className="text-red-500 hover:text-red-700 text-xs transition-colors">Delete</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
