import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../main.dart';

class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});
  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen> {
  @override
  void initState() {
    super.initState();
    _init();
  }

  Future<void> _init() async {
    final app = context.read<AppState>();
    await app.tryAutoLogin();
    if (mounted) {
      Navigator.pushReplacementNamed(context, app.isLoggedIn ? '/home' : '/login');
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    body: Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text('🦋', style: TextStyle(fontSize: 72)),
          const SizedBox(height: 16),
          Text('Tata', style: Theme.of(context).textTheme.headlineLarge),
          const SizedBox(height: 8),
          Text('让想念的人，随时陪在你身边', style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: Colors.grey)),
          const SizedBox(height: 32),
          const CircularProgressIndicator(),
        ],
      ),
    ),
  );
}

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});
  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _emailCtrl = TextEditingController();
  final _passCtrl = TextEditingController();
  bool _loading = false;

  Future<void> _login() async {
    setState(() => _loading = true);
    try {
      await context.read<AppState>().login(_emailCtrl.text, _passCtrl.text);
      if (mounted) Navigator.pushReplacementNamed(context, '/home');
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('登录失败: $e')));
    }
    setState(() => _loading = false);
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    body: SafeArea(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text('🦋', style: TextStyle(fontSize: 64)),
            const SizedBox(height: 8),
            Text('Tata', style: Theme.of(context).textTheme.headlineMedium),
            const SizedBox(height: 32),
            TextField(controller: _emailCtrl, decoration: const InputDecoration(labelText: '邮箱', prefixIcon: Icon(Icons.email))),
            const SizedBox(height: 16),
            TextField(controller: _passCtrl, obscureText: true, decoration: const InputDecoration(labelText: '密码', prefixIcon: Icon(Icons.lock))),
            const SizedBox(height: 24),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: _loading ? null : _login,
                child: _loading ? const CircularProgressIndicator() : const Text('登录', style: TextStyle(fontSize: 18)),
              ),
            ),
          ],
        ),
      ),
    ),
  );
}

class TokenScreen extends StatelessWidget {
  const TokenScreen({super.key});
  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Token 余额')),
    body: const Center(child: Text('Token 管理页面')),
  );
}

class ProfileScreen extends StatelessWidget {
  const ProfileScreen({super.key});
  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('我的')),
    body: const Center(child: Text('个人资料页面')),
  );
}
