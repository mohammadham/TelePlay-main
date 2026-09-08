import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../../lib/api';
import { useState, useEffect } from 'react';

interface SEOData {
  id?: number;
  title_template: string;
  description_template: string;
  keywords: string;
  geo_region: string;
  geo_locale: string;
  geo_list: string;
  social_image: string;
}

export default function SEOSettingsPanel() {
  const qc = useQueryClient();
  const [values, setValues] = useState<SEOData | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ['admin-seo'],
    queryFn: async () => (await api.get('/admin/seo/config')).data,
  });

  useEffect(() => { if (data) setValues(data); }, [data]);

  const save = useMutation({
    mutationFn: async (v: SEOData) => (await api.put('/admin/seo/config', v)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin-seo'] }),
  });

  const seed = useMutation({
    mutationFn: async () => (await api.post('/admin/seo/seed')).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin-seo'] }),
  });

  if (isLoading || !values) return <div className="p-6 space-y-4">{Array.from({length:6}).map((_,i)=><div key={i} className="skeleton h-12 rounded" />)}</div>;

  const set = (key: keyof SEOData, val: string) => setValues({ ...values, [key]: val });

  return (
    <div className="space-y-6 max-w-2xl">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-bold">SEO & Geo Settings</h2>
        <button onClick={() => seed.mutate()} className="btn-secondary text-sm">Seed Defaults</button>
      </div>

      <div className="glass-card p-5 space-y-4">
        {/* Title Template */}
        <label className="flex flex-col gap-1.5">
          <span className="text-sm font-medium">Title Template <span className="text-xs text-dark-500 font-normal">Use {'{title}'} placeholder</span></span>
          <input
            value={values.title_template}
            onChange={e => set('title_template', e.target.value)}
            className="input"
            placeholder="TelePlay | {title}"
          />
          <span className="text-xs text-dark-500">Example: <code className="text-primary-400">{values.title_template}</code></span>
        </label>

        {/* Description */}
        <label className="flex flex-col gap-1.5">
          <span className="text-sm font-medium">Description</span>
          <textarea
            value={values.description_template}
            onChange={e => set('description_template', e.target.value)}
            className="input resize-none"
            rows={3}
            placeholder="TelePlay - stream your files anywhere"
          />
        </label>

        {/* Keywords */}
        <label className="flex flex-col gap-1.5">
          <span className="text-sm font-medium">Keywords</span>
          <input
            value={values.keywords}
            onChange={e => set('keywords', e.target.value)}
            className="input"
            placeholder="telegram, files, streaming, music, video"
          />
        </label>

        {/* Geo List */}
        <label className="flex flex-col gap-1.5">
          <span className="text-sm font-medium">Geo List (AI)</span>
          <input
            value={values.geo_list}
            onChange={e => set('geo_list', e.target.value)}
            className="input"
            placeholder="IR,US,CA"
          />
          <span className="text-xs text-dark-500">AI will format this list</span>
        </label>

        {/* Social Image */}
        <label className="flex flex-col gap-1.5">
          <span className="text-sm font-medium">Social Image URL</span>
          <input
            value={values.social_image}
            onChange={e => set('social_image', e.target.value)}
            className="input"
            placeholder="/api/stream/cover/default"
          />
        </label>
      </div>

      <button
        onClick={() => save.mutate(values)}
        disabled={save.isPending}
        className="btn-primary"
      >
        {save.isPending ? 'Saving...' : 'Save Settings'}
      </button>
    </div>
  );
}
