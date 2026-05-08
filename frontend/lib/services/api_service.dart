import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class ApiService {
  static const String baseUrl = 'http://YOUR_SERVER_IP:8000';
  final _storage = const FlutterSecureStorage();

  String? _token;

  // ── Auth ────────────────────────────────────────────

  Future<String?> getToken() async {
    _token ??= await _storage.read(key: 'auth_token');
    return _token;
  }

  Future<Map<String, dynamic>> login(String email, String password) async {
    final res = await http.post(
      Uri.parse('$baseUrl/auth/login'),
      headers: {'Content-Type': 'application/x-www-form-urlencoded'},
      body: {'username': email, 'password': password},
    );
    final data = jsonDecode(res.body);
    _token = data['access_token'];
    await _storage.write(key: 'auth_token', value: _token);
    return data;
  }

  Future<Map<String, dynamic>> register(String email, String username, String password) async {
    final res = await http.post(
      Uri.parse('$baseUrl/auth/register'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'email': email, 'username': username, 'password': password}),
    );
    return jsonDecode(res.body);
  }

  // ── Profile ─────────────────────────────────────────

  Future<Map<String, dynamic>?> getProfile() async => _get('/profile');
  Future<Map<String, dynamic>> updateProfile(Map<String, dynamic> data) async => _put('/profile', data);

  // ── Personas ────────────────────────────────────────

  Future<List<dynamic>> getPersonas() async {
    final res = await _get('/personas');
    return res is List ? res : [];
  }

  Future<Map<String, dynamic>> getPersona(int id) async => _get('/personas/$id');
  Future<Map<String, dynamic>> createPersona(Map<String, dynamic> data) async => _post('/personas', data);
  Future<Map<String, dynamic>> updatePersona(int id, Map<String, dynamic> data) async => _put('/personas/$id', data);
  Future<void> deletePersona(int id) async => _delete('/personas/$id');

  // ── Chat Logs ───────────────────────────────────────

  Future<Map<String, dynamic>> uploadChatFile(int personaId, String filePath) async {
    final token = await getToken();
    final request = http.MultipartRequest('POST', Uri.parse('$baseUrl/personas/$personaId/chat-logs/upload'));
    request.headers['Authorization'] = 'Bearer $token';
    request.files.add(await http.MultipartFile.fromPath('file', filePath));
    final res = await request.send();
    return jsonDecode(await res.stream.bytesToString());
  }

  Future<Map<String, dynamic>> ocrScreenshot(int personaId, String imagePath) async {
    final token = await getToken();
    final request = http.MultipartRequest('POST', Uri.parse('$baseUrl/personas/$personaId/chat-logs/ocr'));
    request.headers['Authorization'] = 'Bearer $token';
    request.files.add(await http.MultipartFile.fromPath('file', imagePath));
    final res = await request.send();
    return jsonDecode(await res.stream.bytesToString());
  }

  // ── Chat ────────────────────────────────────────────

  Future<Map<String, dynamic>> sendMessage(int personaId, String message, {String provider = 'deepseek'}) async {
    return _post('/chat', {'persona_id': personaId, 'message': message, 'provider': provider});
  }

  Future<List<dynamic>> getChatHistory(int personaId, {int limit = 50}) async {
    final res = await _get('/chat/$personaId/history?limit=$limit');
    return res is List ? res : [];
  }

  // ── Tokens ──────────────────────────────────────────

  Future<Map<String, dynamic>> getTokenBalance() async => _get('/tokens/balance');
  Future<List<dynamic>> getProviders() async {
    final res = await _get('/tokens/providers');
    return res is List ? res : [];
  }

  // ── Payments ────────────────────────────────────────

  Future<Map<String, dynamic>> getTiers() async => _get('/payments/tiers');
  Future<Map<String, dynamic>> checkout(String tier) async => _post('/payments/checkout?tier=$tier', {});

  // ── HTTP Helpers ────────────────────────────────────

  Future<Map<String, dynamic>> _get(String path) async {
    final token = await getToken();
    final res = await http.get(Uri.parse('$baseUrl$path'), headers: _headers(token));
    return _handleResponse(res);
  }

  Future<Map<String, dynamic>> _post(String path, Map<String, dynamic> body) async {
    final token = await getToken();
    final res = await http.post(Uri.parse('$baseUrl$path'), headers: _headers(token), body: jsonEncode(body));
    return _handleResponse(res);
  }

  Future<Map<String, dynamic>> _put(String path, Map<String, dynamic> body) async {
    final token = await getToken();
    final res = await http.put(Uri.parse('$baseUrl$path'), headers: _headers(token), body: jsonEncode(body));
    return _handleResponse(res);
  }

  Future<void> _delete(String path) async {
    final token = await getToken();
    await http.delete(Uri.parse('$baseUrl$path'), headers: _headers(token));
  }

  Map<String, String> _headers(String? token) => {
    'Content-Type': 'application/json',
    if (token != null) 'Authorization': 'Bearer $token',
  };

  Map<String, dynamic> _handleResponse(http.Response res) {
    if (res.statusCode >= 200 && res.statusCode < 300) {
      return jsonDecode(res.body);
    }
    throw ApiException(res.statusCode, jsonDecode(res.body)['detail'] ?? 'Unknown error');
  }
}

class ApiException implements Exception {
  final int statusCode;
  final String message;
  ApiException(this.statusCode, this.message);
  @override
  String toString() => 'API Error $statusCode: $message';
}
