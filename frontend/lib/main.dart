import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:google_fonts/google_fonts.dart';
import 'services/api_service.dart';
import 'screens/splash_screen.dart';
import 'screens/login_screen.dart';
import 'screens/home_screen.dart';
import 'screens/chat_screen.dart';
import 'screens/persona_setup_screen.dart';
import 'screens/profile_screen.dart';
import 'screens/token_screen.dart';

void main() {
  runApp(const TataApp());
}

class TataApp extends StatelessWidget {
  const TataApp({super.key});

  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider(
      create: (_) => AppState(),
      child: MaterialApp(
        title: 'Tata',
        debugShowCheckedModeBanner: false,
        theme: ThemeData(
          useMaterial3: true,
          colorScheme: ColorScheme.fromSeed(
            seedColor: const Color(0xFF6C5CE7),
            brightness: Brightness.light,
          ),
          textTheme: GoogleFonts.notoSansScTextTheme(),
          cardTheme: CardTheme(
            elevation: 0,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
          ),
          appBarTheme: const AppBarTheme(
            centerTitle: true,
            elevation: 0,
            scrolledUnderElevation: 1,
          ),
          elevatedButtonTheme: ElevatedButtonThemeData(
            style: ElevatedButton.styleFrom(
              padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 16),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
            ),
          ),
          inputDecorationTheme: InputDecorationTheme(
            filled: true,
            border: OutlineInputBorder(borderRadius: BorderRadius.circular(16)),
            contentPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
          ),
        ),
        darkTheme: ThemeData(
          useMaterial3: true,
          brightness: Brightness.dark,
          colorScheme: ColorScheme.fromSeed(
            seedColor: const Color(0xFF6C5CE7),
            brightness: Brightness.dark,
          ),
          textTheme: GoogleFonts.notoSansScTextTheme(ThemeData.dark().textTheme),
          cardTheme: CardTheme(
            elevation: 0,
            color: Colors.grey.shade900,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
          ),
          elevatedButtonTheme: ElevatedButtonThemeData(
            style: ElevatedButton.styleFrom(
              padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 16),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
            ),
          ),
          inputDecorationTheme: InputDecorationTheme(
            filled: true,
            fillColor: Colors.grey.shade800,
            border: OutlineInputBorder(borderRadius: BorderRadius.circular(16)),
            contentPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
          ),
        ),
        themeMode: ThemeMode.system,
        initialRoute: '/splash',
        routes: {
          '/splash': (_) => const SplashScreen(),
          '/login': (_) => const LoginScreen(),
          '/home': (_) => const HomeScreen(),
          '/profile': (_) => const ProfileScreen(),
          '/tokens': (_) => const TokenScreen(),
        },
        onGenerateRoute: (settings) {
          if (settings.name == '/chat') {
            final args = settings.arguments as Map<String, dynamic>;
            return MaterialPageRoute(
              builder: (_) => ChatScreen(personaId: args['persona_id'], personaName: args['persona_name']),
            );
          }
          if (settings.name == '/persona_setup') {
            final args = settings.arguments as Map<String, dynamic>?;
            return MaterialPageRoute(
              builder: (_) => PersonaSetupScreen(personaId: args?['persona_id']),
            );
          }
          return null;
        },
      ),
    );
  }
}

class AppState extends ChangeNotifier {
  final ApiService api = ApiService();
  Map<String, dynamic>? _user;
  bool _isLoggedIn = false;

  Map<String, dynamic>? get user => _user;
  bool get isLoggedIn => _isLoggedIn;

  Future<void> tryAutoLogin() async {
    final token = await api.getToken();
    if (token != null) {
      try {
        _user = await api.getProfile();
        _isLoggedIn = true;
        notifyListeners();
      } catch (_) {
        _isLoggedIn = false;
      }
    }
  }

  Future<void> login(String email, String password) async {
    final data = await api.login(email, password);
    _user = data['user'];
    _isLoggedIn = true;
    notifyListeners();
  }

  Future<void> logout() async {
    _user = null;
    _isLoggedIn = false;
    notifyListeners();
  }
}
