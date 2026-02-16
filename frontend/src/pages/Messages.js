import { useState, useEffect, useRef, useCallback } from "react";
import { useWallet } from "@solana/wallet-adapter-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import axios from "axios";
import {
  MessageSquare, Send, ArrowLeft, User, Circle, Wallet
} from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function Messages() {
  const { publicKey, connected } = useWallet();
  const [conversations, setConversations] = useState([]);
  const [selectedConversation, setSelectedConversation] = useState(null);
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState("");
  const [newChatWallet, setNewChatWallet] = useState("");
  const [showNewChat, setShowNewChat] = useState(false);
  const [sending, setSending] = useState(false);
  const [displayName, setDisplayName] = useState(() => localStorage.getItem("bullpugName") || "Guardian");
  const [ws, setWs] = useState(null);
  const messagesEndRef = useRef(null);

  const fetchConversations = useCallback(async () => {
    if (!publicKey) return;
    try {
      const { data } = await axios.get(`${API}/messages/conversations/${publicKey.toBase58()}`);
      setConversations(data.conversations);
    } catch (e) {
      console.error(e);
    }
  }, [publicKey]);

  const fetchMessages = useCallback(async (otherWallet) => {
    if (!publicKey) return;
    try {
      const { data } = await axios.get(
        `${API}/messages/conversation/${publicKey.toBase58()}/${otherWallet}`
      );
      setMessages(data.messages);
    } catch (e) {
      console.error(e);
    }
  }, [publicKey]);

  useEffect(() => {
    if (connected && publicKey) {
      fetchConversations();

      // Connect WebSocket for real-time messages
      const wsUrl = process.env.REACT_APP_BACKEND_URL.replace("https://", "wss://").replace("http://", "ws://");
      const socket = new WebSocket(`${wsUrl}/ws/dm/${publicKey.toBase58()}`);
      
      socket.onmessage = (e) => {
        const msg = JSON.parse(e.data);
        if (msg.type === "new_message") {
          setMessages(prev => [...prev, msg.data]);
          fetchConversations();
        } else if (msg.type === "message_sent") {
          // Message confirmed sent
        }
      };

      socket.onerror = () => console.error("DM WebSocket error");
      setWs(socket);

      return () => socket.close();
    }
  }, [connected, publicKey, fetchConversations]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const selectConversation = (conv) => {
    setSelectedConversation(conv);
    fetchMessages(conv.other_wallet);
  };

  const sendMessage = async () => {
    if (!newMessage.trim() || !selectedConversation || !publicKey) return;
    
    setSending(true);
    try {
      if (ws && ws.readyState === WebSocket.OPEN) {
        // Send via WebSocket for real-time
        ws.send(JSON.stringify({
          type: "send_message",
          to_wallet: selectedConversation.other_wallet,
          content: newMessage,
          from_name: displayName
        }));
      } else {
        // Fallback to REST API
        await axios.post(`${API}/messages/send`, {
          to_wallet: selectedConversation.other_wallet,
          content: newMessage,
          from_wallet: publicKey.toBase58(),
          from_name: displayName
        });
      }
      
      // Optimistically add message
      setMessages(prev => [...prev, {
        id: Date.now().toString(),
        from_wallet: publicKey.toBase58(),
        to_wallet: selectedConversation.other_wallet,
        content: newMessage,
        from_name: displayName,
        created_at: new Date().toISOString()
      }]);
      
      setNewMessage("");
      localStorage.setItem("bullpugName", displayName);
    } catch (e) {
      toast.error("Failed to send message");
    }
    setSending(false);
  };

  const startNewChat = () => {
    if (!newChatWallet.trim()) return toast.error("Enter a wallet address");
    if (newChatWallet === publicKey?.toBase58()) return toast.error("Cannot message yourself");
    
    setSelectedConversation({
      conversation_id: "new",
      other_wallet: newChatWallet,
      other_name: "New Contact"
    });
    setMessages([]);
    setShowNewChat(false);
    setNewChatWallet("");
  };

  if (!connected) {
    return (
      <div className="pt-20 pb-16 min-h-screen">
        <div className="stars-bg fixed inset-0 -z-10" />
        <div className="max-w-4xl mx-auto px-6 py-20 text-center">
          <Wallet className="w-12 h-12 mx-auto mb-4 text-slate-600" />
          <p className="text-slate-400">Connect your wallet to use messages</p>
        </div>
      </div>
    );
  }

  return (
    <div className="pt-20 pb-16 min-h-screen">
      <div className="stars-bg fixed inset-0 -z-10" />
      <div className="max-w-5xl mx-auto px-6">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-black uppercase" style={{ fontFamily: 'Orbitron' }}>
            <MessageSquare className="inline w-6 h-6 mr-2 text-[#00C2FF]" />
            Messages
          </h1>
          <Button
            onClick={() => setShowNewChat(true)}
            className="bg-[#00FFA3] text-black font-bold rounded-xl px-4"
          >
            New Chat
          </Button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 h-[600px]">
          {/* Conversations List */}
          <div className="glass-card rounded-xl p-3 overflow-y-auto">
            <div className="mb-3">
              <Input
                value={displayName}
                onChange={e => setDisplayName(e.target.value)}
                placeholder="Your display name"
                className="bg-black/50 border-white/10 text-white text-sm"
              />
            </div>

            {showNewChat && (
              <div className="p-3 rounded-lg bg-[#00FFA3]/10 border border-[#00FFA3]/30 mb-3">
                <p className="text-xs text-[#00FFA3] mb-2">Start new conversation</p>
                <Input
                  value={newChatWallet}
                  onChange={e => setNewChatWallet(e.target.value)}
                  placeholder="Wallet address"
                  className="bg-black/50 border-white/10 text-white text-xs mb-2"
                />
                <div className="flex gap-2">
                  <Button onClick={startNewChat} size="sm" className="flex-1 bg-[#00FFA3] text-black text-xs">
                    Start
                  </Button>
                  <Button onClick={() => setShowNewChat(false)} size="sm" variant="outline" className="text-xs">
                    Cancel
                  </Button>
                </div>
              </div>
            )}

            {conversations.length === 0 ? (
              <div className="text-center py-10">
                <MessageSquare className="w-8 h-8 mx-auto mb-2 text-slate-700" />
                <p className="text-slate-600 text-sm">No conversations yet</p>
              </div>
            ) : (
              <div className="space-y-2">
                {conversations.map(conv => (
                  <div
                    key={conv.conversation_id}
                    onClick={() => selectConversation(conv)}
                    className={`p-3 rounded-lg cursor-pointer transition-colors ${
                      selectedConversation?.conversation_id === conv.conversation_id
                        ? "bg-[#00C2FF]/10 border border-[#00C2FF]/30"
                        : "bg-white/[0.02] hover:bg-white/[0.05]"
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      <div className="w-8 h-8 rounded-full bg-[#D946EF]/10 flex items-center justify-center text-[#D946EF] text-xs font-bold">
                        {conv.other_name?.charAt(0) || "?"}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between">
                          <p className="text-sm font-bold text-white truncate">{conv.other_name}</p>
                          {conv.unread_count > 0 && (
                            <Badge className="bg-[#00FFA3] text-black text-[9px] px-1.5">
                              {conv.unread_count}
                            </Badge>
                          )}
                        </div>
                        <p className="text-[10px] text-slate-500 truncate">{conv.last_message}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Chat Area */}
          <div className="md:col-span-2 glass-card rounded-xl flex flex-col">
            {selectedConversation ? (
              <>
                {/* Chat Header */}
                <div className="p-4 border-b border-white/10 flex items-center gap-3">
                  <button
                    onClick={() => setSelectedConversation(null)}
                    className="md:hidden text-slate-400 hover:text-white"
                  >
                    <ArrowLeft size={20} />
                  </button>
                  <div className="w-10 h-10 rounded-full bg-[#D946EF]/10 flex items-center justify-center text-[#D946EF] font-bold">
                    {selectedConversation.other_name?.charAt(0) || "?"}
                  </div>
                  <div>
                    <p className="font-bold text-white">{selectedConversation.other_name}</p>
                    <p className="text-[10px] text-slate-500">{selectedConversation.other_wallet?.slice(0, 16)}...</p>
                  </div>
                </div>

                {/* Messages */}
                <div className="flex-1 overflow-y-auto p-4 space-y-3">
                  {messages.map((msg, i) => {
                    const isMe = msg.from_wallet === publicKey?.toBase58();
                    return (
                      <div key={i} className={`flex ${isMe ? "justify-end" : "justify-start"}`}>
                        <div className={`max-w-[70%] p-3 rounded-xl ${
                          isMe 
                            ? "bg-[#00FFA3]/10 border border-[#00FFA3]/30" 
                            : "bg-white/5 border border-white/10"
                        }`}>
                          <p className="text-sm text-white">{msg.content}</p>
                          <p className="text-[9px] text-slate-500 mt-1">
                            {new Date(msg.created_at).toLocaleTimeString()}
                          </p>
                        </div>
                      </div>
                    );
                  })}
                  <div ref={messagesEndRef} />
                </div>

                {/* Input */}
                <div className="p-4 border-t border-white/10">
                  <div className="flex gap-2">
                    <Input
                      value={newMessage}
                      onChange={e => setNewMessage(e.target.value)}
                      placeholder="Type a message..."
                      className="flex-1 bg-black/50 border-white/10 text-white"
                      onKeyDown={e => e.key === "Enter" && !e.shiftKey && sendMessage()}
                    />
                    <Button
                      onClick={sendMessage}
                      disabled={sending || !newMessage.trim()}
                      className="bg-[#00FFA3] text-black"
                    >
                      <Send size={16} />
                    </Button>
                  </div>
                </div>
              </>
            ) : (
              <div className="flex-1 flex items-center justify-center">
                <div className="text-center">
                  <MessageSquare className="w-12 h-12 mx-auto mb-3 text-slate-700" />
                  <p className="text-slate-500">Select a conversation or start a new chat</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
