/**
 * RenameModal - Modal for renaming files and folders
 */
import { useState, useEffect, useRef } from 'react';
import { X } from 'lucide-react';

interface RenameModalProps {
    isOpen: boolean;
    onClose: () => void;
    onRename: (newName: string) => void;
    currentName: string;
    itemType: 'file' | 'folder';
}

export default function RenameModal({ isOpen, onClose, onRename, currentName, itemType }: RenameModalProps) {
    const [name, setName] = useState(currentName);
    const inputRef = useRef<HTMLInputElement>(null);

    useEffect(() => {
        if (isOpen) {
            setName(currentName);
            setTimeout(() => {
                if (inputRef.current) {
                    inputRef.current.focus();
                    // Select filename without extension for files
                    if (itemType === 'file') {
                        const lastDot = currentName.lastIndexOf('.');
                        if (lastDot > 0) {
                            inputRef.current.setSelectionRange(0, lastDot);
                        } else {
                            inputRef.current.select();
                        }
                    } else {
                        inputRef.current.select();
                    }
                }
            }, 50);
        }
    }, [isOpen, currentName, itemType]);

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (name.trim() && name !== currentName) {
            onRename(name.trim());
        }
        onClose();
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm animate-fadeIn">
            <div className="bg-dark-800 rounded-xl border border-dark-600 p-6 w-full max-w-md shadow-2xl">
                <div className="flex items-center justify-between mb-4">
                    <h2 className="text-lg font-semibold text-white">
                        Rename {itemType === 'file' ? 'File' : 'Folder'}
                    </h2>
                    <button onClick={onClose} className="text-dark-400 hover:text-white transition-colors">
                        <X className="w-5 h-5" />
                    </button>
                </div>

                <form onSubmit={handleSubmit}>
                    <input
                        ref={inputRef}
                        type="text"
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        className="w-full px-4 py-3 bg-dark-700 border border-dark-600 rounded-lg text-white placeholder-dark-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                        placeholder={`Enter ${itemType} name`}
                    />

                    <div className="flex gap-3 mt-6">
                        <button
                            type="button"
                            onClick={onClose}
                            className="flex-1 px-4 py-2 bg-dark-700 hover:bg-dark-600 text-white rounded-lg transition-colors"
                        >
                            Cancel
                        </button>
                        <button
                            type="submit"
                            disabled={!name.trim() || name === currentName}
                            className="flex-1 px-4 py-2 bg-primary-600 hover:bg-primary-500 disabled:bg-dark-600 disabled:text-dark-400 text-white rounded-lg transition-colors"
                        >
                            Rename
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}
