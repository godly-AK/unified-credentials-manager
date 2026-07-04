// import 'package:auth_app/firebase_api.dart';
import 'package:auth_app/login.dart';
import 'package:auth_app/signup.dart';
import 'package:flutter/material.dart';
import 'package:biometric_signature/biometric_signature.dart';
// import 'package:firebase_core/firebase_core.dart';
// import 'firebase_options.dart';

void main() async{
  WidgetsFlutterBinding.ensureInitialized();
//   await Firebase.initializeApp(
//     options: DefaultFirebaseOptions.currentPlatform,
// );
  final biometricSignature = BiometricSignature();
  final keyExists = await biometricSignature.biometricKeyExists();
  runApp(MyWidget(keyExists: keyExists ?? false,));
}

class MyWidget extends StatelessWidget {
  MyWidget({super.key, required this.keyExists});
  final bool keyExists;
  @override
  Widget build(BuildContext context) {
    return MaterialApp(home: keyExists ? Login() : Signup(),);
  }
}