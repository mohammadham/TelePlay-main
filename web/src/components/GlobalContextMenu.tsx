import { useEffect, useRef, useState } from 'react';
import { useAppStore } from '../lib/store';
import { TelegramFile, Folder, api } from '../lib/api';
import { Play, Download, Link, Edit, FolderInput, Trash2, Globe, ShieldOff, HardDriveDownload } from 'lucide-react';

export default function GlobalContextMenu() {
    const { activeContextMenu, setActiveContextMenu, setPreviewFile, setMoveItems, setMoveFiles, setDeleteConfirm, setRenameFile, setRenameFolder, selectedFileIds, selectedFiles } = useAppStore();
    const menuRef = useRef<HTMLDivElement>(null);
    const [copiedId, setCopiedId] = useState<string | null>(null);

    // Close menu on escape
    useEffect(() => {
        const handleEscape = (e: KeyboardEvent) => {
            if (e.key === 'Escape') {
                e.stopPropagation();
                setActiveContextMenu(null);
            }
        };
        if (activeContextMenu) {
            document.addEventListener('keydown', handleEscape);
        }
        return () => document.removeEventListener('keydown', handleEscape);
    }, [activeContextMenu, setActiveContextMenu]);

    if (!activeContextMenu) return null;

    const { x, y } = activeContextMenu;
    const isMultiSelect = selectedFileIds.size > 1 && activeContextMenu.type === 'file' && selectedFileIds.has(activeContextMenu.item.id);

    // Adjust position to keep within viewport
    const getMenuPosition = () => {
        const menuWidth = 220;
        const menuHeight = 350; 
        const padding = 10;

        let posX = x;
        let posY = y;

        if (posX + menuWidth > window.innerWidth - padding) {
            posX = window.innerWidth - menuWidth - padding;
        }
        if (posY + menuHeight > window.innerHeight - padding) {
            posY = window.innerHeight - menuHeight - padding;
        }

        return { left: posX, top: posY };
    };

    const position = getMenuPosition();

    const handleAction = (action: () => void) => {
        action();
        setActiveContextMenu(null);
    };

    const handleCopy = async (text: string, id: string) => {
        try {
            await navigator.clipboard.writeText(text);
            setCopiedId(id);
            setTimeout(() => setCopiedId(null), 2000);
        } catch (err) {
            console.error('Failed to copy:', err);
        }
    };

    // --- File Actions ---
    const handlePlay = (file: TelegramFile) => {
        setPreviewFile(file);
    };

    const handleShare = async (file: TelegramFile) => {
        try {
            const { data } = await api.post<TelegramFile>(`/files/${file.id}/share`);
            if (activeContextMenu && activeContextMenu.type === 'file') {
                setActiveContextMenu({ ...activeContextMenu, item: data });
            }
        } catch (error) {
            console.error('Failed to share file:', error);
        }
    };

    const handleRevokeShare = async (file: TelegramFile) => {
        try {
            const { data } = await api.delete<TelegramFile>(`/files/${file.id}/share`);
            if (activeContextMenu && activeContextMenu.type === 'file') {
                setActiveContextMenu({ ...activeContextMenu, item: data });
            }
        } catch (error) {
            console.error('Failed to revoke share:', error);
        }
    };

    const ensurePublicLink = async (file: TelegramFile): Promise<string> => {
        if (file.public_stream_url) {
            return `${window.location.protocol}//${window.location.host}${file.public_stream_url}`;
        }
        try {
            const { data } = await api.post<TelegramFile>(`/files/${file.id}/share`);
            if (data.public_stream_url) {
                if (activeContextMenu && activeContextMenu.type === 'file') {
                    setActiveContextMenu({ ...activeContextMenu, item: data });
                }
                return `${window.location.protocol}//${window.location.host}${data.public_stream_url}`;
            }
        } catch (err) {
            console.error('Failed to create public link:', err);
        }
        const token = localStorage.getItem('access_token');
        const downloadUrl = `${api.defaults.baseURL}/stream/${file.id}?token=${token}`;
        return downloadUrl.startsWith('http')
            ? downloadUrl
            : `${window.location.protocol}//${window.location.host}${downloadUrl}`;
    };

    const handleDownload = async (file: TelegramFile) => {
        try {
            const url = await ensurePublicLink(file);
            const downloadUrl = url + (url.includes('?') ? '&' : '?') + 'download=1';
            const a = document.createElement('a');
            a.href = downloadUrl;
            a.download = file.file_name;
            a.target = '_blank';
            a.rel = 'noopener noreferrer';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
        } catch (err) {
            console.error('Failed to download:', err);
        }
    };

    // --- Render ---

    return (
        <>
            {/* Overlay to catch clicks outside */}
            <div
                className="fixed inset-0 z-[99998]"
                onClick={(e) => {
                    e.stopPropagation();
                    setActiveContextMenu(null);
                }}
            />

            {/* Context Menu */}
            <div
                ref={menuRef}
                className="fixed bg-dark-800/95 backdrop-blur-xl border border-white/[0.08] rounded-xl shadow-2xl py-1.5 min-w-[220px] z-[99999] animate-scale-in"
                style={{
                    left: position.left,
                    top: position.top,
                    transformOrigin: 'top left'
                }}
                onClick={(e) => e.stopPropagation()}
                onContextMenu={(e) => e.preventDefault()}
            >
                {activeContextMenu.type === 'file' ? (
                    // File Context Menu
                    <>
                        {isMultiSelect ? (
                            <>
                                <div className="px-3 py-2 text-xs font-medium text-dark-400 uppercase tracking-wider">
                                    {selectedFileIds.size} Selected
                                </div>
                                <button className="context-menu-item w-full text-left" onClick={() => handleAction(() => setMoveFiles(selectedFiles))}>
                                    <FolderInput className="w-4 h-4" />
                                    Move ({selectedFileIds.size}) Items
                                </button>
                                <button className="context-menu-item w-full text-left text-red-400 hover:bg-red-500/10" onClick={() => handleAction(() => setDeleteConfirm({ type: 'file', items: Array.from(selectedFileIds).map(id => ({ id } as any)) }))}> 
                                    <Trash2 className="w-4 h-4" />
                                    Delete ({selectedFileIds.size}) Items
                                </button>
                            </>
                        ) : (
                            <>
                                {(activeContextMenu.item.file_type === 'video' || activeContextMenu.item.file_type === 'audio') && (
                                    <button className="context-menu-item w-full text-left" onClick={() => handleAction(() => handlePlay(activeContextMenu.item as TelegramFile))}>
                                        <Play className="w-4 h-4" />
                                        Play
                                    </button>
                                )}
                                <button
                                    className="context-menu-item w-full text-left"
                                    onClick={() => { handleDownload(activeContextMenu.item as TelegramFile); setActiveContextMenu(null); }}
                                >
                                    <Download className="w-4 h-4" />
                                    Download
                                </button>
                                
                                <hr className="border-white/[0.08] my-1" />

                                <button className="context-menu-item w-full text-left" onClick={async () => {
                                    const url = await ensurePublicLink(activeContextMenu.item as TelegramFile);
                                    handleCopy(url, 'stream');
                                }}>
                                    <Link className="w-4 h-4" />
                                    {copiedId === 'stream' ? '✓ Copied!' : 'Copy Stream URL'}
                                </button>

                                <button className="context-menu-item w-full text-left" onClick={async () => {
                                    const url = await ensurePublicLink(activeContextMenu.item as TelegramFile);
                                    const downloadUrl = url + (url.includes('?') ? '&' : '?') + 'download=1';
                                    handleCopy(downloadUrl, 'download');
                                }}>
                                    <HardDriveDownload className="w-4 h-4" />
                                    {copiedId === 'download' ? '✓ Copied!' : 'Copy Download URL'}
                                </button>

                                <hr className="border-white/[0.08] my-1" />

                                {(activeContextMenu.item as TelegramFile).public_stream_url ? (
                                    <>
                                        <button className="context-menu-item w-full text-left" onClick={() => handleCopy(`${window.location.protocol}//${window.location.host}${(activeContextMenu.item as TelegramFile).public_stream_url}`, 'public')}>
                                            <Globe className="w-4 h-4 text-emerald-400" />
                                            {copiedId === 'public' ? '✓ Copied!' : 'Copy Public Link'}
                                        </button>
                                        <button className="context-menu-item w-full text-left text-orange-400 hover:bg-orange-500/10" onClick={() => handleRevokeShare(activeContextMenu.item as TelegramFile)}>
                                            <ShieldOff className="w-4 h-4" />
                                            Revoke Public Link
                                        </button>
                                    </>
                                ) : (
                                    <button className="context-menu-item w-full text-left" onClick={() => handleShare(activeContextMenu.item as TelegramFile)}>
                                        <Globe className="w-4 h-4" />
                                        Create Public Link
                                    </button>
                                )}

                                <hr className="border-white/[0.08] my-1" />
                                
                                <button className="context-menu-item w-full text-left" onClick={() => handleAction(() => setRenameFile(activeContextMenu.item as TelegramFile))}>
                                    <Edit className="w-4 h-4" />
                                    Rename
                                </button>
                                <button className="context-menu-item w-full text-left" onClick={() => handleAction(() => setMoveItems({ files: [activeContextMenu.item as TelegramFile], folders: [] }))}>
                                    <FolderInput className="w-4 h-4" />
                                    Move to...
                                </button>
                                
                                <hr className="border-white/[0.08] my-1" />
                                
                                <button className="context-menu-item w-full text-left text-red-400 hover:bg-red-500/10" onClick={() => handleAction(() => setDeleteConfirm({ type: 'file', items: [activeContextMenu.item] }))}>
                                    <Trash2 className="w-4 h-4" />
                                    Delete
                                </button>
                            </>
                        )}
                    </>
                ) : (
                    // Folder Context Menu
                    <>
                        <button
                            className="context-menu-item w-full text-left"
                            onClick={() => handleAction(() => setRenameFolder(activeContextMenu.item as Folder))}
                        >
                            <Edit className="w-4 h-4" />
                            Rename
                        </button>
                        <hr className="border-white/[0.08] my-1" />
                        <button
                            className="context-menu-item w-full text-left text-red-400 hover:bg-red-500/10"
                            onClick={() => handleAction(() => setDeleteConfirm({ type: 'folder', items: [activeContextMenu.item] }))}
                        >
                            <Trash2 className="w-4 h-4" />
                            Delete
                        </button>
                    </>
                )}
            </div>
        </>
    );
}
