import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../main.dart';
import '../services/api_service.dart';

class ChatScreen extends StatefulWidget {
  final int personaId;
  final String personaName;
  const ChatScreen({super.key, required this.personaId, required this.personaName});

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final _msgCtrl = TextEditingController();
  final _scrollCtrl = ScrollController();
  List<Map<String, dynamic>> _messages = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _loadHistory();
  }

  Future<void> _loadHistory() async {
    try {
      final api = context.read<AppState>().api;
      final history = await api.getChatHistory(widget.personaId);
      setState(() { _messages = history.cast<Map<String, dynamic>>(); _loading = false; });
    } catch (_) {
      setState(() => _loading = false);
    }
  }

  Future<void> _sendMessage() async {
    final text = _msgCtrl.text.trim();
    if (text.isEmpty) return;
    _msgCtrl.clear();
    setState(() => _messages.add({'role': 'user', 'content': text}));

    try {
      final api = context.read<AppState>().api;
      final res = await api.sendMessage(widget.personaId, text);
      setState(() => _messages.add({'role': 'ai', 'content': res['reply']}));
      _scrollToBottom();
    } catch (e) {
      setState(() => _messages.add({'role': 'ai', 'content': '消息发送失败: $e'}));
    }
  }

  void _scrollToBottom() {
    Future.delayed(const Duration(milliseconds: 100), () {
      _scrollCtrl.animateTo(_scrollCtrl.position.maxScrollExtent, duration: const Duration(milliseconds: 300), curve: Curves.easeOut);
    });
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.personaName),
        actions: [
          IconButton(icon: const Icon(Icons.tune), tooltip: '调整人格', onPressed: () async {
            final result = await Navigator.pushNamed(context, '/persona_setup', arguments: {'persona_id': widget.personaId});
            if (result == true) _loadHistory();
          }),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : Column(
              children: [
                Expanded(
                  child: ListView.builder(
                    controller: _scrollCtrl,
                    padding: const EdgeInsets.all(16),
                    itemCount: _messages.length,
                    itemBuilder: (_, i) => _buildBubble(_messages[i], theme),
                  ),
                ),
                _buildInputBar(theme),
              ],
            ),
    );
  }

  Widget _buildBubble(Map<String, dynamic> msg, ThemeData theme) {
    final isUser = msg['role'] == 'user';
    return Align(
      alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.symmetric(vertical: 4),
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width * 0.75),
        decoration: BoxDecoration(
          color: isUser ? theme.colorScheme.primary : theme.colorScheme.surfaceContainerHighest,
          borderRadius: BorderRadius.only(
            topLeft: const Radius.circular(20),
            topRight: const Radius.circular(20),
            bottomLeft: isUser ? const Radius.circular(20) : const Radius.circular(4),
            bottomRight: isUser ? const Radius.circular(4) : const Radius.circular(20),
          ),
        ),
        child: Text(
          msg['content'] ?? '',
          style: TextStyle(color: isUser ? theme.colorScheme.onPrimary : theme.colorScheme.onSurface),
        ),
      ),
    );
  }

  Widget _buildInputBar(ThemeData theme) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.05), blurRadius: 10)],
      ),
      child: Row(
        children: [
          Expanded(
            child: TextField(
              controller: _msgCtrl,
              decoration: const InputDecoration(hintText: '说点什么...', border: InputBorder.none),
              maxLines: 4, minLines: 1,
              onSubmitted: (_) => _sendMessage(),
            ),
          ),
          const SizedBox(width: 8),
          CircleAvatar(
            backgroundColor: theme.colorScheme.primary,
            child: IconButton(icon: const Icon(Icons.send, color: Colors.white), onPressed: _sendMessage),
          ),
        ],
      ),
    );
  }
}
