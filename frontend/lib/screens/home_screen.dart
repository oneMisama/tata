import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:google_fonts/google_fonts.dart';
import '../main.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});
  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  List<dynamic> _personas = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _loadPersonas();
  }

  Future<void> _loadPersonas() async {
    try {
      final api = context.read<AppState>().api;
      final list = await api.getPersonas();
      setState(() { _personas = list; _loading = false; });
    } catch (_) {
      setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final app = context.watch<AppState>();
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Tata 🦋'),
        actions: [
          IconButton(icon: const Icon(Icons.account_balance_wallet), tooltip: 'Tokens', onPressed: () => Navigator.pushNamed(context, '/tokens')),
          IconButton(icon: const Icon(Icons.person), tooltip: '我的', onPressed: () => Navigator.pushNamed(context, '/profile')),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () async {
          final result = await Navigator.pushNamed(context, '/persona_setup');
          if (result == true) _loadPersonas();
        },
        icon: const Icon(Icons.add),
        label: const Text('创建人格'),
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _personas.isEmpty
              ? Center(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text('🦋', style: TextStyle(fontSize: 80)),
                      const SizedBox(height: 16),
                      Text('还没有创建人格', style: theme.textTheme.titleMedium),
                      const SizedBox(height: 8),
                      Text('点击下方按钮，创建你的第一个TA', style: TextStyle(color: Colors.grey)),
                    ],
                  ),
                )
              : RefreshIndicator(
                  onRefresh: _loadPersonas,
                  child: ListView.builder(
                    padding: const EdgeInsets.all(16),
                    itemCount: _personas.length,
                    itemBuilder: (_, i) {
                      final p = _personas[i];
                      return Card(
                        margin: const EdgeInsets.only(bottom: 12),
                        child: ListTile(
                          leading: CircleAvatar(
                            radius: 28,
                            backgroundColor: theme.colorScheme.primaryContainer,
                            child: Text(p['name']?.toString()[0] ?? '?', style: const TextStyle(fontSize: 24)),
                          ),
                          title: Text(p['name'] ?? '', style: const TextStyle(fontWeight: FontWeight.w600)),
                          subtitle: Text(p['speaking_style']?.toString().substring(0, 30) ?? ''),
                          trailing: const Icon(Icons.chevron_right),
                          onTap: () => Navigator.pushNamed(context, '/chat', arguments: {
                            'persona_id': p['id'],
                            'persona_name': p['name'],
                          }).then((_) => _loadPersonas()),
                        ),
                      );
                    },
                  ),
                ),
    );
  }
}
