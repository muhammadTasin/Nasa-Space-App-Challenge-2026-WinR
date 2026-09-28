import { RotationEngine } from './packages/rotation-engine/src/engine.ts';
import { FeatureRegistry } from './packages/rotation-engine/src/registry.ts';
import { DualGateNarrationValidator, type ILocalLLMClient } from './packages/narration-core/src/dual_gate_validator.ts';
import { TemplateNarrator } from './packages/narration-core/src/template_narrator.ts';

async function runTests() {
  console.log('========================================================');
  console.log('  EDEN Engine & Dual-Gate Narration Test Suite  ');
  console.log('========================================================\n');

  // TEST 1: Rotation Engine Initialization & Deterministic Replay
  console.log('[TEST 1] Testing Deterministic Rotation Engine for Talanda Union...');
  const engine = new RotationEngine();
  const advice = engine.generateAdvice({
    unionId: 'talanda_tanore',
    unionNameBangla: 'তালন্দ ইউনিয়ন',
    upazila: 'Tanore',
    district: 'Rajshahi',
    landType: 'medium_high',
    season: '2026-aman',
    farmerPriorities: {
      water: 0.5,
      income: 0.3,
      soil: 0.2,
    },
  });

  console.log(`Generated Advice ID: ${advice.advice_id}`);
  console.log(`Number of candidate rotations: ${advice.options.length}`);
  console.log(`Top recommended rotation: ${advice.options[0].nameBangla}`);
  console.log(`Top rotation score: ${advice.options[0].totalWeightedScore}`);
  console.log(`Scores breakdown:`, advice.options[0].scores);

  if (advice.options[0].id !== 'rot_dhan71_lentil') {
    throw new Error(`Expected rot_dhan71_lentil to be ranked #1, got: ${advice.options[0].id}`);
  }
  console.log('✓ TEST 1 PASSED: BRRI dhan71 -> Lentil is correctly ranked #1.\n');

  // TEST 2: Pluggable Feature Registry (Minus Feature)
  console.log('[TEST 2] Testing Plug-and-Play Feature Registry (Disabling Flood Dimension)...');
  const registry = engine.getRegistry();
  console.log(`Active plugins before: ${registry.getActivePlugins().map(p => p.id).join(', ')}`);

  registry.setFeatureFlag('flood', false);
  console.log(`Active plugins after disabling flood: ${registry.getActivePlugins().map(p => p.id).join(', ')}`);

  const adviceWithoutFlood = engine.generateAdvice({
    unionId: 'talanda_tanore',
    unionNameBangla: 'তালন্দ ইউনিয়ন',
    upazila: 'Tanore',
    district: 'Rajshahi',
    landType: 'medium_high',
    season: '2026-aman',
    farmerPriorities: { water: 0.6, income: 0.4 },
  });

  if (adviceWithoutFlood.active_plugins.includes('flood')) {
    throw new Error('Flood dimension was supposed to be inactive!');
  }
  console.log(`Scores without flood:`, adviceWithoutFlood.options[0].scores);
  console.log('✓ TEST 2 PASSED: Feature minus successful with dynamic re-weighting.\n');

  // TEST 3: Deterministic Template Narrator
  console.log('[TEST 3] Testing Deterministic Bangla Template Narrator...');
  const templateNarrator = new TemplateNarrator();
  const templateResult = templateNarrator.render(advice);
  console.log(`Template Bangla Speech: "${templateResult.banglaSpeechText}"`);
  console.log(`Keypad Prompt: "${templateResult.banglaKeypadPrompt}"`);
  if (!templateResult.banglaSpeechText.includes('তালন্দ') || !templateResult.banglaSpeechText.includes('ব্রি ধান৭১')) {
    throw new Error('Template text missing critical union or variety name!');
  }
  console.log('✓ TEST 3 PASSED: Template narration is fluent and verified.\n');

  // TEST 4: Dual-Gate Pipeline with Compliant Local LLM
  console.log('[TEST 4] Testing Dual-Gate Pipeline with Compliant Local LLM...');
  const compliantLLM: ILocalLLMClient = {
    async generate(prompt: string) {
      return 'তালন্দ ইউনিয়নের জন্য ব্রি ধান৭১ ও মসুর চাষ সবচেয়ে লাভজনক। ২৫ মৌসুমে মাত্র ৬ বার বাড়তি সেচ লেগেছে এবং ১০ নভেম্বরের মধ্যে ধান কাটা শেষ হবে।';
    },
  };
  const validatorCompliant = new DualGateNarrationValidator(compliantLLM);
  const resultCompliant = await validatorCompliant.narrate(advice);
  console.log(`Engine used: ${resultCompliant.status}`);
  console.log(`Audit Log:`, resultCompliant.auditLog);
  if (resultCompliant.status !== 'local_model_checked') {
    throw new Error('Expected local_model_checked for compliant LLM output!');
  }
  console.log('✓ TEST 4 PASSED: Compliant LLM passed Gate 1 and Gate 2.\n');

  // TEST 5: Dual-Gate Pipeline with Adversarial / Hallucinating LLM
  console.log('[TEST 5] Testing Dual-Gate Pipeline against Hallucinating LLM (Fake numbers & forbidden loan)...');
  const adversarialLLM: ILocalLLMClient = {
    async generate(prompt: string) {
      // Injects unapproved number "৭ টন" and forbidden word "ঋণ"
      return 'এই জাত লাগালে ৭ টন ফলন পাওয়া যাবে এবং ৫০ কেজি ইউরিয়া সার লাগবে। কৃষি ব্যাংক থেকে ঋণ নিন।';
    },
  };
  const validatorAdversarial = new DualGateNarrationValidator(adversarialLLM);
  const resultAdversarial = await validatorAdversarial.narrate(advice);
  console.log(`Engine used after rejection: ${resultAdversarial.status}`);
  console.log(`Unapproved numbers caught by Gate 2:`, resultAdversarial.auditLog.unapprovedNumbersFound);
  console.log(`Unapproved actions caught by Gate 2:`, resultAdversarial.auditLog.unapprovedActionsFound);
  console.log(`Safe Fallback Speech Text: "${resultAdversarial.banglaSpeechText}"`);

  if (resultAdversarial.status !== 'fallback_template') {
    throw new Error('Expected fallback_template for adversarial LLM output!');
  }
  if (!resultAdversarial.auditLog.unapprovedNumbersFound.includes('৭') && !resultAdversarial.auditLog.unapprovedNumbersFound.includes('7')) {
    throw new Error('Gate 2 failed to catch hallucinated number 7!');
  }
  console.log('✓ TEST 5 PASSED: Adversarial hallucination caught and safely rejected to Template.\n');

  console.log('========================================================');
  console.log('  ALL 5 CORE TESTS PASSED SUCCESSFULLY!                 ');
  console.log('========================================================');
}

runTests().catch(err => {
  console.error('Test failed:', err);
  process.exit(1);
});
