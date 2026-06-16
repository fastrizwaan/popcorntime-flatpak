'use strict';

/**
 * Fetches streams from Torrentio API
 * @param {string} type 'movie' or 'series'
 * @param {string} imdb_id 
 * @param {string|number} season (optional)
 * @param {string|number} episode (optional)
 * @returns {Promise<Array>} Array of torrent objects
 */
module.exports = async function getTorrentioStreams(type, imdb_id, season, episode) {
  let url = '';
  if (type === 'movie') {
    url = `https://torrentio.strem.fun/stream/movie/${imdb_id}.json`;
  } else if (type === 'series') {
    url = `https://torrentio.strem.fun/stream/series/${imdb_id}:${season}:${episode}.json`;
  } else {
    return [];
  }

  try {
    const fetchFunc = typeof window !== 'undefined' && window.fetch ? window.fetch : fetch;
    const response = await fetchFunc(url, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
      }
    });
    
    if (!response.ok) {
      console.warn(`Torrentio fetch failed with status ${response.status} for ${url}`);
      return [];
    }
    
    const data = await response.json();
    if (!data || !data.streams) {
      return [];
    }

    return data.streams.map(s => {
      const titleLines = s.title.split('\n');
      const streamName = (s.name || '').replace('Torrentio\n', '').trim();
      
      const seedMatch = s.title.match(/👤\s*(\d+)/);
      const sizeMatch = s.title.match(/💾\s*([^\s]+)\s*([A-Z]+)/);
      
      const seeds = seedMatch ? parseInt(seedMatch[1], 10) : 0;
      const sizeStr = sizeMatch ? `${sizeMatch[1]} ${sizeMatch[2]}` : 'Unknown';
      
      const quality = `Torrentio ${streamName}${sizeMatch ? ' ' + sizeStr : ''}`;
      
      return {
        quality: quality,
        provider: 'Torrentio',
        title: titleLines[0].trim(),
        url: s.url || `magnet:?xt=urn:btih:${s.infoHash}`,
        magnet: s.url || `magnet:?xt=urn:btih:${s.infoHash}`,
        seed: seeds,
        peers: seeds, // Fallback to seeds if peers aren't explicitly provided
        size: 0, // Butter uses size_bytes but fallback to 0 is usually fine
        filesize: sizeStr
      };
    });
  } catch (error) {
    console.warn(`Torrentio fetch failed for ${url}:`, error);
    return [];
  }
};
