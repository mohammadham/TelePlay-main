/**
 * SEO hook for music pages.
 * Sets document title and meta description for better SEO/social sharing.
 */
import { useEffect } from 'react'

interface SEOProps {
  title: string
  description?: string
}

export function useSEO({ title, description }: SEOProps) {
  useEffect(() => {
    document.title = `${title} | TelePlay`

    // Update meta description
    const metaDesc = document.querySelector('meta[name="description"]')
    if (metaDesc) {
      metaDesc.setAttribute('content', description || 'Stream your Telegram files')
    }

    // Update Open Graph tags
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
      ogDesc.setAttribute('content', description || 'Stream your Telegram files')
    } else {
      const tag = document.createElement('meta')
      tag.setAttribute('property', 'og:description')
      tag.content = description || 'Stream your Telegram files'
      document.head.appendChild(tag)
    }

    // Cleanup
    return () => {
      document.title = 'TelePlay'
      const metaDesc = document.querySelector('meta[name="description"]')
      if (metaDesc) {
        metaDesc.setAttribute('content', 'Stream your Telegram files on any device')
      }
    }
  }, [title, description])
}
