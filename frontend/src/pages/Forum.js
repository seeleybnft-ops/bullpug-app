import { useState, useEffect } from "react";
import { useWallet } from "@solana/wallet-adapter-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import axios from "axios";
import {
  MessageSquare, Plus, Heart, Clock, User, ArrowLeft, Send, Tag
} from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const CATEGORY_COLORS = {
  general: { bg: "bg-slate-500/10", text: "text-slate-400", border: "border-slate-500/30" },
  trading: { bg: "bg-[#00FFA3]/10", text: "text-[#00FFA3]", border: "border-[#00FFA3]/30" },
  betting: { bg: "bg-[#D946EF]/10", text: "text-[#D946EF]", border: "border-[#D946EF]/30" },
  memes: { bg: "bg-[#F5D300]/10", text: "text-[#F5D300]", border: "border-[#F5D300]/30" },
  support: { bg: "bg-[#00C2FF]/10", text: "text-[#00C2FF]", border: "border-[#00C2FF]/30" },
  announcements: { bg: "bg-red-500/10", text: "text-red-400", border: "border-red-500/30" },
};

export default function Forum() {
  const { publicKey, connected } = useWallet();
  const [posts, setPosts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState(null);
  const [selectedPost, setSelectedPost] = useState(null);
  const [showNewPost, setShowNewPost] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchPosts();
    fetchCategories();
  }, [selectedCategory]);

  const fetchPosts = async () => {
    setLoading(true);
    try {
      const url = selectedCategory 
        ? `${API}/forum/posts?category=${selectedCategory}&limit=50`
        : `${API}/forum/posts?limit=50`;
      const { data } = await axios.get(url);
      setPosts(data.posts);
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  const fetchCategories = async () => {
    try {
      const { data } = await axios.get(`${API}/forum/categories`);
      setCategories(data.categories);
    } catch (e) {
      console.error(e);
    }
  };

  const openPost = async (postId) => {
    try {
      const { data } = await axios.get(`${API}/forum/post/${postId}`);
      setSelectedPost(data);
    } catch (e) {
      toast.error("Failed to load post");
    }
  };

  return (
    <div className="pt-20 pb-16 min-h-screen">
      <div className="stars-bg fixed inset-0 -z-10" />
      <div className="max-w-5xl mx-auto px-6 md:px-12">
        {selectedPost ? (
          <PostView 
            post={selectedPost} 
            onBack={() => { setSelectedPost(null); fetchPosts(); }}
            walletAddress={publicKey?.toBase58()}
            connected={connected}
          />
        ) : showNewPost ? (
          <NewPostForm 
            onBack={() => setShowNewPost(false)}
            onSuccess={() => { setShowNewPost(false); fetchPosts(); }}
            walletAddress={publicKey?.toBase58()}
            connected={connected}
            categories={categories}
          />
        ) : (
          <>
            <div className="flex items-center justify-between mb-8">
              <div>
                <h1 className="text-3xl sm:text-4xl font-black tracking-tighter uppercase" style={{ fontFamily: 'Orbitron, sans-serif' }}>
                  Community <span className="text-[#D946EF]">Forum</span>
                </h1>
                <p className="text-slate-500 text-sm mt-1">Join the Bullpug guardian community</p>
              </div>
              <Button
                onClick={() => setShowNewPost(true)}
                disabled={!connected}
                data-testid="new-post-btn"
                className="bg-[#00FFA3] text-black font-bold rounded-xl px-6 py-5 text-sm uppercase hover:scale-[1.02] transition-transform"
              >
                <Plus className="w-4 h-4 mr-2" /> New Post
              </Button>
            </div>

            {!connected && (
              <div className="glass-card rounded-xl p-4 mb-6 border border-amber-500/30 bg-amber-500/5">
                <p className="text-amber-400 text-sm">Connect your wallet to post and reply</p>
              </div>
            )}

            {/* Categories */}
            <div className="flex flex-wrap gap-2 mb-6">
              <button
                onClick={() => setSelectedCategory(null)}
                className={`px-4 py-2 rounded-lg text-xs font-bold uppercase transition-colors ${
                  !selectedCategory ? "bg-[#00FFA3]/10 text-[#00FFA3] border border-[#00FFA3]/30" : "bg-white/5 text-slate-400 border border-white/10 hover:bg-white/10"
                }`}
              >
                All
              </button>
              {categories.map(cat => {
                const colors = CATEGORY_COLORS[cat.id] || CATEGORY_COLORS.general;
                return (
                  <button
                    key={cat.id}
                    onClick={() => setSelectedCategory(cat.id)}
                    className={`px-4 py-2 rounded-lg text-xs font-bold uppercase transition-colors ${
                      selectedCategory === cat.id 
                        ? `${colors.bg} ${colors.text} border ${colors.border}` 
                        : "bg-white/5 text-slate-400 border border-white/10 hover:bg-white/10"
                    }`}
                  >
                    {cat.name}
                  </button>
                );
              })}
            </div>

            {/* Posts List */}
            {loading ? (
              <div className="glass-card rounded-xl p-10 text-center">
                <MessageSquare className="w-10 h-10 mx-auto mb-3 text-slate-600 animate-pulse" />
                <p className="text-slate-500">Loading posts...</p>
              </div>
            ) : posts.length === 0 ? (
              <div className="glass-card rounded-xl p-10 text-center">
                <MessageSquare className="w-10 h-10 mx-auto mb-3 text-slate-700" />
                <p className="text-slate-500">No posts yet</p>
                <p className="text-xs text-slate-600 mt-1">Be the first to start a discussion!</p>
              </div>
            ) : (
              <div className="space-y-3">
                {posts.map(post => {
                  const colors = CATEGORY_COLORS[post.category] || CATEGORY_COLORS.general;
                  return (
                    <div 
                      key={post.id}
                      onClick={() => openPost(post.id)}
                      className="glass-card rounded-xl p-5 cursor-pointer hover:bg-white/[0.03] transition-colors"
                      data-testid={`post-${post.id}`}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-2">
                            <Badge className={`text-[9px] ${colors.bg} ${colors.text} ${colors.border}`}>
                              {post.category}
                            </Badge>
                            {post.likes > 0 && (
                              <span className="text-[10px] text-red-400 flex items-center gap-1">
                                <Heart size={10} fill="currentColor" /> {post.likes}
                              </span>
                            )}
                          </div>
                          <h3 className="text-lg font-bold text-white mb-1">{post.title}</h3>
                          <p className="text-sm text-slate-400 line-clamp-2">{post.content}</p>
                        </div>
                        <div className="text-right ml-4">
                          <div className="flex items-center gap-1 text-xs text-slate-500">
                            <MessageSquare size={12} />
                            {post.reply_count || 0}
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center justify-between mt-3 pt-3 border-t border-white/5">
                        <div className="flex items-center gap-2">
                          <div className="w-6 h-6 rounded-full bg-[#D946EF]/10 flex items-center justify-center text-[#D946EF] text-[10px] font-bold">
                            {post.author_name?.charAt(0) || "?"}
                          </div>
                          <span className="text-xs text-slate-500">{post.author_name}</span>
                        </div>
                        <span className="text-[10px] text-slate-600 flex items-center gap-1">
                          <Clock size={10} />
                          {new Date(post.created_at).toLocaleDateString()}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

function PostView({ post, onBack, walletAddress, connected }) {
  const [reply, setReply] = useState("");
  const [sending, setSending] = useState(false);
  const [displayName, setDisplayName] = useState(() => localStorage.getItem("bullpugName") || "Guardian");
  const [currentPost, setCurrentPost] = useState(post);

  const submitReply = async () => {
    if (!reply.trim()) return toast.error("Enter a reply");
    if (!connected) return toast.error("Connect wallet first");

    setSending(true);
    try {
      await axios.post(`${API}/forum/reply`, {
        post_id: currentPost.id,
        content: reply,
        author_wallet: walletAddress,
        author_name: displayName
      });
      toast.success("Reply posted!");
      localStorage.setItem("bullpugName", displayName);
      setReply("");
      // Refresh post
      const { data } = await axios.get(`${API}/forum/post/${currentPost.id}`);
      setCurrentPost(data);
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed to post reply");
    }
    setSending(false);
  };

  const likePost = async () => {
    if (!connected) return toast.error("Connect wallet first");
    try {
      const { data } = await axios.post(`${API}/forum/like/post/${currentPost.id}?wallet_address=${walletAddress}`);
      setCurrentPost(prev => ({ ...prev, likes: prev.likes + (data.liked ? 1 : -1) }));
    } catch (e) {
      console.error(e);
    }
  };

  const colors = CATEGORY_COLORS[currentPost.category] || CATEGORY_COLORS.general;

  return (
    <div>
      <button onClick={onBack} className="flex items-center gap-2 text-sm text-slate-400 hover:text-white mb-6">
        <ArrowLeft size={16} /> Back to Forum
      </button>

      <div className="glass-card rounded-2xl p-6 mb-6">
        <div className="flex items-center gap-2 mb-3">
          <Badge className={`text-[10px] ${colors.bg} ${colors.text} ${colors.border}`}>
            {currentPost.category}
          </Badge>
        </div>
        <h1 className="text-2xl font-black text-white mb-3">{currentPost.title}</h1>
        <p className="text-slate-300 whitespace-pre-wrap">{currentPost.content}</p>
        
        <div className="flex items-center justify-between mt-6 pt-4 border-t border-white/10">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-[#D946EF]/10 flex items-center justify-center text-[#D946EF] font-bold">
              {currentPost.author_name?.charAt(0) || "?"}
            </div>
            <div>
              <p className="text-sm font-bold text-white">{currentPost.author_name}</p>
              <p className="text-[10px] text-slate-500">{currentPost.author_wallet?.slice(0, 12)}...</p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <button 
              onClick={likePost}
              className="flex items-center gap-1 text-sm text-slate-400 hover:text-red-400 transition-colors"
            >
              <Heart size={16} className={currentPost.likes > 0 ? "fill-red-400 text-red-400" : ""} />
              {currentPost.likes}
            </button>
            <span className="text-xs text-slate-500">
              {new Date(currentPost.created_at).toLocaleString()}
            </span>
          </div>
        </div>
      </div>

      {/* Replies */}
      <div className="mb-6">
        <h3 className="text-sm font-bold uppercase text-slate-500 mb-4">
          {currentPost.replies?.length || 0} Replies
        </h3>
        
        {currentPost.replies && currentPost.replies.length > 0 ? (
          <div className="space-y-3">
            {currentPost.replies.map(r => (
              <div key={r.id} className="glass-card rounded-xl p-4">
                <p className="text-slate-300 text-sm">{r.content}</p>
                <div className="flex items-center justify-between mt-3 pt-3 border-t border-white/5">
                  <div className="flex items-center gap-2">
                    <div className="w-6 h-6 rounded-full bg-[#00C2FF]/10 flex items-center justify-center text-[#00C2FF] text-[10px] font-bold">
                      {r.author_name?.charAt(0) || "?"}
                    </div>
                    <span className="text-xs text-slate-500">{r.author_name}</span>
                  </div>
                  <span className="text-[10px] text-slate-600">
                    {new Date(r.created_at).toLocaleString()}
                  </span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="glass-card rounded-xl p-6 text-center">
            <p className="text-slate-600 text-sm">No replies yet. Be the first!</p>
          </div>
        )}
      </div>

      {/* Reply Form */}
      <div className="glass-card rounded-xl p-4">
        <div className="flex items-center gap-3 mb-3">
          <Input 
            value={displayName}
            onChange={e => setDisplayName(e.target.value)}
            placeholder="Your name"
            maxLength={30}
            className="w-32 bg-black/50 border-white/10 text-white text-sm"
          />
          <span className="text-xs text-slate-500">replying as</span>
        </div>
        <div className="flex gap-2">
          <Input
            value={reply}
            onChange={e => setReply(e.target.value)}
            placeholder="Write a reply..."
            className="flex-1 bg-black/50 border-white/10 text-white"
            onKeyDown={e => e.key === "Enter" && !e.shiftKey && submitReply()}
          />
          <Button 
            onClick={submitReply}
            disabled={sending || !connected}
            className="bg-[#00FFA3] text-black font-bold rounded-lg px-4"
          >
            <Send size={16} />
          </Button>
        </div>
      </div>
    </div>
  );
}

function NewPostForm({ onBack, onSuccess, walletAddress, connected, categories }) {
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [category, setCategory] = useState("general");
  const [displayName, setDisplayName] = useState(() => localStorage.getItem("bullpugName") || "Guardian");
  const [posting, setPosting] = useState(false);

  const submitPost = async () => {
    if (!title.trim()) return toast.error("Enter a title");
    if (!content.trim()) return toast.error("Enter content");
    if (!connected) return toast.error("Connect wallet first");

    setPosting(true);
    try {
      await axios.post(`${API}/forum/post`, {
        title,
        content,
        category,
        author_wallet: walletAddress,
        author_name: displayName
      });
      toast.success("Post created!");
      localStorage.setItem("bullpugName", displayName);
      onSuccess();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed to create post");
    }
    setPosting(false);
  };

  return (
    <div>
      <button onClick={onBack} className="flex items-center gap-2 text-sm text-slate-400 hover:text-white mb-6">
        <ArrowLeft size={16} /> Back to Forum
      </button>

      <div className="glass-card rounded-2xl p-6">
        <h2 className="text-xl font-black uppercase mb-6" style={{ fontFamily: 'Orbitron' }}>
          New Post
        </h2>

        <div className="space-y-4">
          <div>
            <label className="text-xs text-slate-500 uppercase mb-1 block">Your Name</label>
            <Input 
              value={displayName}
              onChange={e => setDisplayName(e.target.value)}
              maxLength={30}
              className="bg-black/50 border-white/10 text-white"
            />
          </div>

          <div>
            <label className="text-xs text-slate-500 uppercase mb-1 block">Category</label>
            <div className="flex flex-wrap gap-2">
              {categories.map(cat => {
                const colors = CATEGORY_COLORS[cat.id] || CATEGORY_COLORS.general;
                return (
                  <button
                    key={cat.id}
                    onClick={() => setCategory(cat.id)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-colors ${
                      category === cat.id 
                        ? `${colors.bg} ${colors.text} border ${colors.border}` 
                        : "bg-white/5 text-slate-400 border border-white/10 hover:bg-white/10"
                    }`}
                  >
                    {cat.name}
                  </button>
                );
              })}
            </div>
          </div>

          <div>
            <label className="text-xs text-slate-500 uppercase mb-1 block">Title</label>
            <Input 
              value={title}
              onChange={e => setTitle(e.target.value)}
              placeholder="What's on your mind?"
              maxLength={200}
              className="bg-black/50 border-white/10 text-white"
              data-testid="post-title-input"
            />
          </div>

          <div>
            <label className="text-xs text-slate-500 uppercase mb-1 block">Content</label>
            <textarea
              value={content}
              onChange={e => setContent(e.target.value)}
              placeholder="Share your thoughts with the community..."
              maxLength={5000}
              rows={8}
              className="w-full bg-black/50 border border-white/10 rounded-lg p-3 text-white text-sm resize-none"
              data-testid="post-content-input"
            />
            <p className="text-[10px] text-slate-600 text-right">{content.length}/5000</p>
          </div>

          <div className="flex gap-3 pt-4">
            <Button onClick={onBack} variant="outline" className="flex-1 border-white/20 text-slate-400 rounded-xl py-5">
              Cancel
            </Button>
            <Button 
              onClick={submitPost}
              disabled={posting || !connected}
              data-testid="submit-post-btn"
              className="flex-1 bg-[#00FFA3] text-black font-bold rounded-xl py-5"
            >
              {posting ? "Posting..." : "Create Post"}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
