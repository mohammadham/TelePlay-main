import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../../lib/api';
import { useState, useEffect } from 'react';
import { Sparkles, X, Check } from 'lucide-react';

const COUNTRIES = [
  { code: 'IR', name: 'Iran', flag: '🇮🇷' },
  { code: 'US', name: 'United States', flag: '🇺🇸' },
  { code: 'CA', name: 'Canada', flag: '🇨🇦' },
  { code: 'GB', name: 'United Kingdom', flag: '🇬🇧' },
  { code: 'DE', name: 'Germany', flag: '🇩🇪' },
  { code: 'FR', name: 'France', flag: '🇫🇷' },
  { code: 'AU', name: 'Australia', flag: '🇦🇺' },
  { code: 'JP', name: 'Japan', flag: '🇯🇵' },
  { code: 'KR', name: 'South Korea', flag: '🇰🇷' },
  { code: 'CN', name: 'China', flag: '🇨🇳' },
  { code: 'IN', name: 'India', flag: '🇮🇳' },
  { code: 'BR', name: 'Brazil', flag: '🇧🇷' },
  { code: 'RU', name: 'Russia', flag: '🇷🇺' },
  { code: 'TR', name: 'Turkey', flag: '🇹🇷' },
  { code: 'SA', name: 'Saudi Arabia', flag: '🇸🇦' },
  { code: 'AE', name: 'UAE', flag: '🇦🇪' },
  { code: 'QA', name: 'Qatar', flag: '🇶🇦' },
  { code: 'KW', name: 'Kuwait', flag: '🇰🇼' },
  { code: 'BH', name: 'Bahrain', flag: '🇧🇭' },
  { code: 'OM', name: 'Oman', flag: '🇴🇲' },
  { code: 'EG', name: 'Egypt', flag: '🇪🇬' },
  { code: 'MA', name: 'Morocco', flag: '🇲🇦' },
  { code: 'TN', name: 'Tunisia', flag: '🇹🇳' },
  { code: 'PK', name: 'Pakistan', flag: '🇵🇰' },
  { code: 'BD', name: 'Bangladesh', flag: '🇧🇩' },
  { code: 'ID', name: 'Indonesia', flag: '🇮🇩' },
  { code: 'MY', name: 'Malaysia', flag: '🇲🇾' },
  { code: 'TH', name: 'Thailand', flag: '🇹🇭' },
  { code: 'VN', name: 'Vietnam', flag: '🇻🇳' },
  { code: 'PH', name: 'Philippines', flag: '🇵🇭' },
];

interface SEOData {
  id?: number;
  title_template: string;
  description_template: string;
  keywords: string;
  ai_agent_description: string;
  geo_region: string;
  geo_locale: string;
  geo_list: string;
  social_image: string;
}

export default function SEOSettingsPanel() {
  const qc = useQueryClient();
  const [values, setValues] = useState<SEOData | null>(null);
  const [showCountryPicker, setShowCountryPicker] = useState(false);

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

  // Parse geo_list as JSON array
  const selectedCountries = useState(() => {
    if (!values?.geo_list) return ['IR'];
    try {
      const parsed = JSON.parse(values.geo_list);
      return Array.isArray(parsed) ? parsed : [values.geo_list];
    } catch {
      return [values.geo_list];
    }
  })[0];

  const setSelectedCountries = (countries: string[]) => {
    if (values) {
      setValues({ ...values, geo_list: JSON.stringify(countries) });
    }
  };

  const toggleCountry = (code: string) => {
    const current = selectedCountries.includes(code)
      ? selectedCountries.filter(c => c !== code)
      : [...selectedCountries, code];
    setSelectedCountries(current);
  };

  const aiSuggest = () => {
    // Simulate AI suggestion based on common streaming regions
    const suggestions = ['IR', 'US', 'CA', 'GB', 'DE', 'FR', 'AE', 'SA', 'TR', 'AU'];
    setSelectedCountries(suggestions);
  };

  if (isLoading || !values) return <div className="p-6 space-y-4">{Array.from({length:6}).map((_,i)=><div key={i} className="skeleton h-12 rounded" />)}</div>;

  const set = (key: keyof SEOData, val: string) => setValues({ ...values, [key]: val });

  return (
    <div className="space-y-6 max-w-3xl">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-bold">SEO & Geo Settings</h2>
        <button onClick={() => seed.mutate()} className="btn-secondary text-sm">Seed Defaults</button>
      </div>

      <div className="glass-card p-5 space-y-4">
        {/* Title Template */}
        <label className="flex flex-col gap-1.5">
          <span className="text-sm font-medium">
            Title Template <span className="text-xs text-dark-500 font-normal">Use {'{title}'} placeholder</span>
          </span>
          <input value={values.title_template} onChange={e => set('title_template', e.target.value)} className="input" placeholder="TelePlay | {title}" />
          <span className="text-xs text-dark-500">Example: <code className="text-primary-400">{values.title_template}</code></span>
        </label>

        {/* Description */}
        <label className="flex flex-col gap-1.5">
          <span className="text-sm font-medium">Description</span>
          <textarea value={values.description_template} onChange={e => set('description_template', e.target.value)} className="input resize-none" rows={3} placeholder="TelePlay - stream your files anywhere" />
        </label>

        {/* AI Agent Description */}
        <label className="flex flex-col gap-1.5">
          <span className="text-sm font-medium">
            AI Agent Description
            <span className="text-xs text-dark-500 font-normal ml-2">For AI assistants and search engines</span>
          </span>
          <textarea value={values.ai_agent_description} onChange={e => set('ai_agent_description', e.target.value)} className="input resize-none" rows={3} placeholder="TelePlay is a media streaming platform that allows users to stream audio, video, and reels from Telegram file storage." />
          <span className="text-xs text-dark-500">This helps AI agents understand your site content and structure.</span>
        </label>

        {/* Keywords */}
        <label className="flex flex-col gap-1.5">
          <span className="text-sm font-medium">Keywords</span>
          <input value={values.keywords} onChange={e => set('keywords', e.target.value)} className="input" placeholder="telegram, files, streaming, music, video" />
        </label>

        {/* Geo Region & Locale */}
        <div className="grid grid-cols-2 gap-4">
          <label className="flex flex-col gap-1.5">
            <span className="text-sm font-medium">Geo Region (Primary)</span>
            <input value={values.geo_region} onChange={e => set('geo_region', e.target.value)} className="input" placeholder="IR" />
          </label>
          <label className="flex flex-col gap-1.5">
            <span className="text-sm font-medium">Geo Locale</span>
            <input value={values.geo_locale} onChange={e => set('geo_locale', e.target.value)} className="input" placeholder="fa" />
          </label>
        </div>

        {/* Geo List (AI) */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">Geo Regions (AI)</span>
            <div className="flex gap-2">
              <button onClick={aiSuggest} className="btn-secondary text-xs flex items-center gap-1">
                <Sparkles className="w-3 h-3" /> Suggest
              </button>
              <button onClick={() => setShowCountryPicker(!showCountryPicker)} className="btn-secondary text-xs">
                {showCountryPicker ? 'Close' : 'Edit List'}
              </button>
            </div>
          </div>

          {showCountryPicker && (
            <div className="p-3 bg-[#1a1a1a] rounded-lg border border-white/10 max-h-60 overflow-y-auto">
              <div className="grid grid-cols-3 gap-2">
                {COUNTRIES.map(country => (
                  <button
                    key={country.code}
                    onClick={() => toggleCountry(country.code)}
                    className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-all ${
                      selectedCountries.includes(country.code)
                        ? 'bg-primary-600/30 border border-primary-500/50 text-white'
                        : 'bg-white/5 border border-white/10 text-white/60 hover:bg-white/10'
                    }`}
                  >
                    <span>{country.flag}</span>
                    <span className="truncate">{country.code}</span>
                    {selectedCountries.includes(country.code) && <Check className="w-3 h-3 ml-auto text-primary-400" />}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Display selected countries */}
          <div className="flex flex-wrap gap-2 pt-2">
            {selectedCountries.length === 0 ? (
              <span className="text-xs text-dark-500">No regions selected</span>
            ) : (
              selectedCountries.map(code => {
                const country = COUNTRIES.find(c => c.code === code);
                return (
                  <span key={code} className="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-white/10 text-xs text-white/80">
                    {country?.flag} {code}
                    <button onClick={() => toggleCountry(code)} className="ml-1 text-white/40 hover:text-white">
                      <X className="w-3 h-3" />
                    </button>
                  </span>
                );
              })
            )}
          </div>
          <span className="text-xs text-dark-500">Select regions for geo-targeting. AI suggests top streaming markets.</span>
        </div>

        {/* Social Image */}
        <label className="flex flex-col gap-1.5">
          <span className="text-sm font-medium">Social Image URL</span>
          <input value={values.social_image} onChange={e => set('social_image', e.target.value)} className="input" placeholder="/api/stream/cover/default" />
        </label>
      </div>

      <button onClick={() => save.mutate(values)} disabled={save.isPending} className="btn-primary">
        {save.isPending ? 'Saving...' : 'Save Settings'}
      </button>
    </div>
  );
}
