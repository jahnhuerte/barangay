<?php

namespace App\Http\Controllers;

use App\Jobs\RunPythonScript;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;

class RecommendationController extends Controller
{
    public function index()
    {
        // Get top requested programs from residents
        $topPrograms = DB::table('residents')
            ->select('programId', DB::raw('COUNT(programId) as usage_count'))
            ->groupBy('programId')
            ->orderByDesc('usage_count')
            ->limit(10)
            ->get();

        // Get priority-based recommendations based on service requests
        $priorityPrograms = DB::table('recommendations')
        ->leftJoin('blotters', 'recommendations.programId', '=', 'blotters.programId')
         ->leftJoin('clearances', 'recommendations.programId', '=', 'clearances.programId') // REMOVE this line
        ->leftJoin('medical_requests', 'recommendations.programId', '=', 'medical_requests.programId')
        ->leftJoin('job_applications', 'recommendations.programId', '=', 'job_applications.programId')
        ->leftJoin('housing_requests', 'recommendations.programId', '=', 'housing_requests.programId')
        ->leftJoin('financial_assistance', 'recommendations.programId', '=', 'financial_assistance.programId')
        ->select('recommendations.programId', 'recommendations.programName', 'recommendations.programDescription',
            'recommendations.priority', DB::raw(
                'COUNT(blotters.id) * 1.8 + 
                 COUNT(medical_requests.id) * 2.5 + 
                 COUNT(job_applications.id) * 1.5 + 
                 COUNT(housing_requests.id) * 2.0 + 
                 COUNT(financial_assistance.id) * 1.7 as weighted_request_count'
            ))
        ->groupBy('recommendations.programId')
        ->orderByDesc('weighted_request_count')
        ->limit(10)
        ->get();
    

        // Merge and prioritize recommendations
        $mergedPrograms = collect($topPrograms)->merge($priorityPrograms);
        $mergedPrograms = $mergedPrograms->sortByDesc(function ($program) {
            return ($program->priority == 'High' ? 3 : ($program->priority == 'Medium' ? 2 : 1)) + ($program->usage_count ?? 0);
        });

        // Dispatch Python script for additional analytics
        RunPythonScript::dispatch();

        // Pass the data to the view
        return view('re  commendation.index', ['programDetails' => $mergedPrograms]);
    }
}
