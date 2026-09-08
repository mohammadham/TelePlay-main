/**
 * SEO hook for music pages.
 * Sets document title, meta description, Open Graph tags, canonical URL, and JSON-LD structured data.
 */
import { useEffect } from 'react'

interface SEOProps {
  title: string
  description?: string
  canonicalUrl?: string
  /** Schema.org type: website | music_group | music_album | music_track | music_playlist */
  type?: 'website' | 'music_group' | 'music_album' | 'music_track' | 'music_playlist'
  image?: string
  duration?: string
  /** For music_track/music_playlist: tracks data */
  artists?: Array<{ name: string; verified?: boolean; avatarUrl?: string }>
  numTracks?: number
}

const SITE_URL = 'https://teleplay-main-production.up.railway.app'

export function useSEO({ title, description, canonicalUrl, type, image, duration, artists, numTracks }: SEOProps) {
  useEffect(() => {
    // Set page title
    document.title = `${title} | TelePlay`

    // Update meta description
    let metaDesc = document.querySelector('meta[name="description"]')
    if (metaDesc) {
      metaDesc.setAttribute('content', description || 'Stream your Telegram files anywhere')
    } else {
      metaDesc = document.createElement('meta')
      metaDesc.setAttribute('name', 'description')
      metaDesc.content = description || 'Stream your Telegram files anywhere'
      document.head.appendChild(metaDesc)
    }

    // Canonical URL
    let canonical = document.querySelector('link[rel="canonical"]')
    const canonHref = canonicalUrl || `${SITE_URL}${window.location.pathname}`
    if (canonical) {
      canonical.setAttribute('href', canonHref)
    } else {
      canonical = document.createElement('link')
      canonical.setAttribute('rel', 'canonical')
      canonical.setAttribute('href', canonHref)
      document.head.appendChild(canonical)
    }

    // Open Graph tags
    const ogTitle = document.querySelector('meta[property="og:title"]')
    if (ogTitle) {
      ogTitle.setAttribute('content', `${title} | TelePlay`)
    } else {
      const tag = document.createElement('meta')
      tag.setAttribute('property', 'og:title')
      tag.content = `${title} | TelePlay`
      document.head.appendChild(tag)
    }

    const ogDesc = document.querySelector('meta[property="og:description"]')
    if (ogDesc) {
      ogDesc.setAttribute('content', description || 'Stream your Telegram files anywhere')
    } else {
      const tag = document.createElement('meta')
      tag.setAttribute('property', 'og:description')
      tag.content = description || 'Stream your Telegram files anywhere'
      document.head.appendChild(tag)
    }

    const ogUrl = document.querySelector('meta[property="og:url"]')
    if (ogUrl) {
      ogUrl.setAttribute('content', canonHref)
    } else {
      const tag = document.createElement('meta')
      tag.setAttribute('property', 'og:url')
      tag.content = canonHref
      document.head.appendChild(tag)
    }

    const ogType = document.querySelector('meta[property="og:type"]')
    if (ogType) {
      ogType.setAttribute('content', type === 'website' ? 'website' : 'music.song')
    } else {
      const tag = document.createElement('meta')
      tag.setAttribute('property', 'og:type')
      tag.content = type === 'website' ? 'website' : 'music.song'
      document.head.appendChild(tag)
    }

    if (image) {
      const ogImage = document.querySelector('meta[property="og:image"]')
      if (ogImage) {
        ogImage.setAttribute('content', image)
      } else {
        const tag = document.createElement('meta')
        tag.setAttribute('property', 'og:image')
        tag.content = image
        document.head.appendChild(tag)
      }

      const twitterImage = document.querySelector('meta[name="twitter:image"]')
      if (twitterImage) {
        twitterImage.setAttribute('content', image)
      } else {
        const tag = document.createElement('meta')
        tag.setAttribute('name', 'twitter:image')
        tag.content = image
        document.head.appendChild(tag)
      }
    }

    // JSON-LD structured data
    const existingScript = document.querySelector('script[data-seo-type]')
    if (existingScript) {
      existingScript.remove()
    }

    let ldData: Record<string, unknown> | null = null

    if (type === 'music_track') {
      ldData = {
        '@context': 'https://schema.org',
        '@type': 'MusicRecording',
        name: title,
        duration: duration,
        url: canonHref,
        ...(image && { image }),
        ...(artists?.[0] && {
          byArtist: {
            '@type': 'MusicGroup',
            name: artists[0].name,
          },
        }),
      }
    } else if (type === 'music_group') {
      ldData = {
        '@context': 'https://schema.org',
        '@type': 'MusicGroup',
        name: title,
        url: canonHref,
        ...(image && { image }),
        ...(artists?.[0]?.verified && { sameAs: [canonHref] }),
      }
    } else if (type === 'music_playlist') {
      ldData = {
        '@context': 'https://schema.org',
        '@type': 'MusicPlaylist',
        name: title,
        url: canonHref,
        numTracks: numTracks,
        ...(image && { image }),
        ...(artists?.length && {
          track: artists.slice(0, 10).map((a, i) => ({
            '@type': 'MusicRecording',
            name: a.name,
            position: i + 1,
            ...(a.duration && { duration: a.duration }),
          })),
        }),
      }
    } else if (type === 'music_album') {
      ldData = {
        '@context': 'https://schema.org',
        '@type': 'MusicAlbum',
        name: title,
        url: canonHref,
        ...(image && { image }),
        ...(artists?.[0] && {
          byArtist: {
            '@type': 'MusicGroup',
            name: artists[0].name,
          },
        }),
      }
    }

    if (ldData) {
      const script = document.createElement('script')
      script.type = 'application/ld+json'
      script.setAttribute('data-seo-type', type || 'unknown')
      script.text = JSON.stringify(ldData)
      document.head.appendChild(script)
    }

    // Cleanup
    return () => {
      document.title = 'TelePlay'
      if (metaDesc) metaDesc.setAttribute('content', 'Stream your Telegram files on any device')
      if (canonical) canonical.remove()
      document.querySelectorAll('meta[property^="og:"]').forEach(el => el.remove())
      document.querySelectorAll('meta[name="twitter:"]').forEach(el => el.remove())
      document.querySelectorAll('script[data-seo-type]').forEach(el => el.remove())
    }
  }, [title, description, canonicalUrl, type, image, duration, artists, numTracks])
}
