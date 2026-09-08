/**
 * Structured data component for JSON-LD schema injection.
 * Supports Organization, WebSite, MusicGroup, MusicAlbum, MusicTrack, MusicPlaylist schemas.
 */
import { useEffect } from 'react'

interface OrganizationSchema {
  '@context': string
  '@type': string
  name: string
  url: string
  description: string
  image?: string
  sameAs?: string[]
}

interface WebSiteSchema {
  '@context': string
  '@type': string
  name: string
  url: string
  description: string
  inLanguage?: string
  publisher?: OrganizationSchema
}

interface MusicGroupSchema {
  '@context': string
  '@type': string
  name: string
  description?: string
  url?: string
  image?: string
  sameAs?: string[]
}

interface MusicAlbumSchema {
  '@context': string
  '@type': string
  name: string
  artist: { '@type': string; name: string }
  track?: {
    '@type': string
    name: string
    duration?: string
    position?: number
    album?: { '@type': string; name: string }
  }[]
  url?: string
  image?: string
}

interface MusicTrackSchema {
  '@context': string
  '@type': string
  name: string
  artist: { '@type': string; name: string }
  album?: { '@type': string; name: string }
  duration?: string
  url?: string
  image?: string
  playCount?: number
}

interface MusicPlaylistSchema {
  '@context': string
  '@type': string
  name: string
  track?: {
    '@type': string
    name: string
    duration?: string
    position?: number
    artist?: { '@type': string; name: string }
  }[]
  url?: string
  image?: string
  numTracks?: number
}

interface BreadcrumbSchema {
  '@context': string
  '@type': string
  itemListElement: {
    '@type': string
    position: number
    item: { '@type': string; id: string; name: string }
  }[]
}

interface Props {
  type: 'organization' | 'website' | 'music_group' | 'music_album' | 'music_track' | 'music_playlist' | 'breadcrumb'
  data: OrganizationSchema | WebSiteSchema | MusicGroupSchema | MusicAlbumSchema | MusicTrackSchema | MusicPlaylistSchema | BreadcrumbSchema
}

export default function StructuredData({ type, data }: Props) {
  useEffect(() => {
    const script = document.createElement('script')
    script.type = 'application/ld+json'
    script.text = JSON.stringify(data)
    document.head.appendChild(script)

    return () => {
      document.head.removeChild(script)
    }
  }, [type, data])

  return null
}
